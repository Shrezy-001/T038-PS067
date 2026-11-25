from .models import Assignment, Violation
from .ordering_heuristic import order_courses
from .constraint_checker import ConstraintChecker
from .hall_allocator import pack_courses


class ExamScheduler:
    """
    Earliest-valid-session scheduler with both student and physical-hall capacity
    checks. The optional unavailable_halls set uses (hall_id, date, session).
    """

    def __init__(self, data, unavailable_halls=None):
        self.data = data
        self.violations = []
        self.checker = ConstraintChecker(data)
        self.unavailable_halls = set(unavailable_halls or ())

    def _sessions(self):
        rows = [
            row for row in self.data["exam_window"]
            if str(row.get("available", "")).strip().upper() in ("YES", "TRUE", "1")
        ]
        return sorted(rows, key=lambda r: (
            r["date"], 0 if r["session"] == "FN" else 1
        ))

    def _capacity_ok(self, candidate, session, assignments):
        key = (session["date"], session["session"])
        current = [
            a for a in assignments
            if (a.date, a.session) == key
        ] + [candidate]

        available_halls = [
            h for h in self.data["halls"]
            if (h["hall_id"], session["date"], session["session"])
            not in self.unavailable_halls
        ]
        if not available_halls:
            return False

        total_capacity = sum(int(h["capacity"]) for h in available_halls)
        total_students = sum(len(a.students) for a in current)
        if total_students > int(total_capacity * 0.90):
            return False

        return pack_courses(
            self.data, current, self.data["halls"], self.unavailable_halls
        )

    def generate(self):
        self.violations = []
        sessions = self._sessions()
        if not sessions:
            raise ValueError("No available exam sessions")

        assignments = []
        used_by_session = {}
        courses = order_courses(self.data["courses"])

        # Calendar dates include holidays; only available session rows are candidates.
        calendar_dates = sorted({row["date"] for row in self.data["exam_window"]})
        final_three = set(calendar_dates[-3:])

        for course in courses:
            code = course["course_code"]
            students = list(self.data["course_students"].get(code, []))
            enrolment = len(students)
            backlog = str(course.get("exam_type", "REGULAR")).strip().upper() == "BACKLOG"

            eligible = [
                s for s in sessions
                if not backlog or (
                    s["date"] in final_three
                    and (
                        s["session"] == "AN"
                        or (enrolment > 50 and s["session"] == "FN")
                    )
                )
            ]

            placed = None
            gap_fallback = None
            last_reason = "no eligible session"

            for slot in eligible:
                candidate = Assignment(
                    code, slot["date"], slot["session"],
                    int(course["exam_duration_hours"]), students, []
                )

                ok, soft, reason = self.checker.can_assign(
                    course, slot["date"], slot["session"], assignments
                )
                if not ok:
                    last_reason = reason or last_reason
                    ok_soft, soft_messages, soft_reason = self.checker.can_assign(
                        course, slot["date"], slot["session"], assignments,
                        allow_gap_violation=True
                    )
                    if ok_soft and soft_messages:
                        if self._capacity_ok(candidate, slot, assignments) and gap_fallback is None:
                            gap_fallback = (slot, soft_messages)
                    continue

                if not self._capacity_ok(candidate, slot, assignments):
                    last_reason = "hall count, duration compatibility or 90% capacity limit"
                    continue

                placed = (slot, soft)
                break

            if placed is None and gap_fallback is not None:
                placed = gap_fallback

            if placed is None:
                self.violations.append(Violation(
                    "BR-01/02/04/06/07/12", "HARD", code,
                    f"No available session satisfies student and hall constraints ({last_reason})"
                ))
                continue

            slot, soft = placed
            assignment = Assignment(
                code, slot["date"], slot["session"],
                int(course["exam_duration_hours"]), students, list(soft)
            )
            assignments.append(assignment)
            key = (assignment.date, assignment.session)
            used_by_session[key] = used_by_session.get(key, 0) + enrolment
            self.checker.register(course, assignment.date, assignment.session)

            for message in soft:
                self.violations.append(Violation("BR-04", "SOFT", code, message))

        return assignments
