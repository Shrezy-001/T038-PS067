from .models import HallAssignment


def _course_meta(data, assignment):
    course = data["course_by_code"].get(assignment.course_code, {})
    return {
        "assignment": assignment,
        "code": assignment.course_code,
        "department": course.get("department", ""),
        "duration": int(assignment.duration),
        "students": list(assignment.students),
    }


def pack_courses(data, assignments, halls, unavailable=None):
    """
    Deterministic bin-packing feasibility check.
    One hall can host at most two courses, only if durations match,
    departments differ, and combined enrolment fits its capacity.
    """
    unavailable = unavailable or set()
    available_halls = [
        h for h in halls
        if (h["hall_id"], assignments[0].date, assignments[0].session) not in unavailable
    ] if assignments else list(halls)

    bins = [
        {"hall": h, "remaining": int(h["capacity"]), "duration": None,
         "departments": set(), "courses": []}
        for h in sorted(available_halls, key=lambda x: (-int(x["capacity"]), x["hall_id"]))
    ]

    items = [_course_meta(data, a) for a in assignments]
    items.sort(key=lambda x: (-len(x["students"]), -x["duration"], x["code"]))

    for item in items:
        count = len(item["students"])
        candidates = []
        for b in bins:
            if b["remaining"] < count or len(b["courses"]) >= 2:
                continue
            if b["duration"] is not None and b["duration"] != item["duration"]:
                continue
            if b["courses"] and item["department"] in b["departments"]:
                continue
            candidates.append(b)
        if not candidates:
            return False
        # Prefer pairing, then the smallest fitting hall to preserve large halls.
        candidates.sort(key=lambda b: (
            0 if b["courses"] else 1,
            b["remaining"],
            b["hall"]["hall_id"]
        ))
        chosen = candidates[0]
        chosen["remaining"] -= count
        chosen["duration"] = item["duration"]
        chosen["departments"].add(item["department"])
        chosen["courses"].append(item["code"])
    return True


class HallAllocator:
    """Allocates each session using the same two-course-per-hall feasibility rules."""

    def __init__(self, data):
        self.data = data
        self.violations = []

    def allocate(self, assignments, unavailable=None):
        self.violations = []
        unavailable = unavailable or set()
        grouped = {}
        for assignment in assignments:
            grouped.setdefault((assignment.date, assignment.session), []).append(assignment)

        result = []
        halls = sorted(
            self.data["halls"],
            key=lambda h: (-int(h["capacity"]), h["hall_id"])
        )

        for (date, session), session_assignments in sorted(grouped.items()):
            available_halls = [
                h for h in halls
                if (h["hall_id"], date, session) not in unavailable
            ]
            bins = [
                {"hall": h, "remaining": int(h["capacity"]), "duration": None,
                 "departments": set(), "courses": [], "students": []}
                for h in available_halls
            ]

            items = [_course_meta(self.data, a) for a in session_assignments]
            items.sort(key=lambda x: (-len(x["students"]), -x["duration"], x["code"]))

            for item in items:
                count = len(item["students"])
                candidates = []
                for b in bins:
                    if b["remaining"] < count or len(b["courses"]) >= 2:
                        continue
                    if b["duration"] is not None and b["duration"] != item["duration"]:
                        continue
                    if b["courses"] and item["department"] in b["departments"]:
                        continue
                    candidates.append(b)

                if not candidates:
                    self.violations.append({
                        "rule_id": "BR-06/07",
                        "severity": "HARD",
                        "entity": item["code"],
                        "message": (
                            f"{count} students could not be seated in {date} {session}; "
                            "no compatible hall remained"
                        ),
                    })
                    continue

                candidates.sort(key=lambda b: (
                    0 if b["courses"] else 1,
                    b["remaining"],
                    b["hall"]["hall_id"]
                ))
                chosen = candidates[0]
                chosen["remaining"] -= count
                chosen["duration"] = item["duration"]
                chosen["departments"].add(item["department"])
                chosen["courses"].append(item["code"])
                chosen["students"].extend(item["students"])

            for b in bins:
                if not b["courses"]:
                    continue
                result.append(HallAssignment(
                    date, session, b["hall"]["hall_id"],
                    list(b["courses"]), list(b["students"]),
                    int(b["duration"])
                ))

        return result
