from .models import HallAssignment


def _course_meta(data, assignment):
    course = data["course_by_code"].get(assignment.course_code, {})
    students = list(assignment.students)
    return {
        "assignment": assignment,
        "code": assignment.course_code,
        "department": str(course.get("department", "")).strip().upper(),
        "duration": int(assignment.duration),
        "students": students,
        "count": len(students),
        "has_special_needs": any(
            str(data["student_by_id"].get(sid, {}).get("special_needs", "NO")).strip().upper()
            in {"YES", "TRUE", "1"}
            for sid in students
        ),
    }


def _column_capacity(hall, course_position):
    rows = int(hall["rows"])
    columns = int(hall["columns"])
    usable_columns = (columns + 1) // 2 if course_position == 0 else columns // 2
    return rows * usable_columns


def _hall_compatible(bin_data, item, position=None):
    hall = bin_data["hall"]
    if position is None:
        position = len(bin_data["courses"])
    if len(bin_data["courses"]) >= 2:
        return False
    if bin_data["remaining"] < item["count"]:
        return False
    if bin_data["duration"] is not None and bin_data["duration"] != item["duration"]:
        return False
    if bin_data["courses"] and item["department"] in bin_data["departments"]:
        return False
    if item["has_special_needs"] and str(hall.get("floor", "")).strip().upper() != "GROUND":
        return False
    if bin_data["special"] and str(hall.get("floor", "")).strip().upper() != "GROUND":
        return False
    if item["count"] > _column_capacity(hall, position):
        return False
    if position == 1 and bin_data["course_counts"][0] > _column_capacity(hall, 0):
        return False
    # BR-05: a course with fewer than 10 students cannot be the only
    # course in a hall. It must be paired with a different department.
    if item["count"] < 10 and not bin_data["courses"]:
        return False
    return True


def _place(bin_data, item):
    bin_data["remaining"] -= item["count"]
    bin_data["duration"] = item["duration"]
    bin_data["departments"].add(item["department"])
    bin_data["courses"].append(item["code"])
    bin_data["course_counts"].append(item["count"])
    bin_data["students"].extend(item["students"])
    bin_data["special"] = bin_data["special"] or item["has_special_needs"]


def _new_bins(halls):
    return [
        {
            "hall": hall,
            "remaining": int(hall["capacity"]),
            "duration": None,
            "departments": set(),
            "courses": [],
            "course_counts": [],
            "students": [],
            "special": False,
        }
        for hall in sorted(halls, key=lambda h: (-int(h["capacity"]), str(h["hall_id"])))
    ]


def _allocate_session(data, assignments, halls):
    """Greedy largest-first packing, with deterministic pairing of small courses."""
    bins = _new_bins(halls)
    items = [_course_meta(data, assignment) for assignment in assignments]
    items.sort(key=lambda x: (not x["has_special_needs"], -x["count"], -x["duration"], x["code"]))

    # Allocate courses of 10+ first, preserving the specified course priority.
    # Small courses are deferred so they can be merged rather than stranded.
    regular = [item for item in items if item["count"] >= 10]
    small = [item for item in items if item["count"] < 10]
    unplaced = []

    for item in regular:
        chosen = next((b for b in bins if _hall_compatible(b, item)), None)
        if chosen is None:
            unplaced.append(item)
        else:
            _place(chosen, item)

    for item in small:
        # Prefer the largest already-occupied compatible hall.
        chosen = next((b for b in bins if b["courses"] and _hall_compatible(b, item)), None)
        if chosen is not None:
            _place(chosen, item)
        else:
            unplaced.append(item)

    # Any small courses that could not join a larger course must be paired
    # with another small course from a different department, same duration.
    pending = list(unplaced)
    unplaced = []
    while pending:
        first = pending.pop(0)
        partner_index = next((i for i, other in enumerate(pending)
            if other["department"] != first["department"]
            and other["duration"] == first["duration"]), None)
        if first["count"] < 10 and partner_index is None:
            unplaced.append(first)
            continue
        if first["count"] >= 10:
            chosen = next((b for b in bins if _hall_compatible(b, first)), None)
            if chosen is None:
                unplaced.append(first)
            else:
                _place(chosen, first)
            continue

        partner = pending.pop(partner_index)
        pair = [first, partner]
        pair_special = any(x["has_special_needs"] for x in pair)
        chosen = None
        for b in bins:
            if b["courses"] or b["remaining"] < sum(x["count"] for x in pair):
                continue
            if b["duration"] is not None and b["duration"] != first["duration"]:
                continue
            if pair_special and str(b["hall"].get("floor", "")).strip().upper() != "GROUND":
                continue
            if first["count"] > _column_capacity(b["hall"], 0):
                continue
            if partner["count"] > _column_capacity(b["hall"], 1):
                continue
            chosen = b
            break
        if chosen is None:
            unplaced.extend(pair)
        else:
            _place(chosen, first)
            _place(chosen, partner)

    return bins, unplaced


def pack_courses(data, assignments, halls, unavailable=None):
    """Return whether all courses can be packed under hall constraints."""
    if not assignments:
        return True
    unavailable = unavailable or set()
    date, session = assignments[0].date, assignments[0].session
    available_halls = [h for h in halls if (h["hall_id"], date, session) not in unavailable]
    _, unplaced = _allocate_session(data, assignments, available_halls)
    return not unplaced


class HallAllocator:
    """Allocate each session using largest-first hall selection and BR-05 rules."""

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
        for (date, session), session_assignments in sorted(grouped.items()):
            available_halls = [
                hall for hall in self.data["halls"]
                if (hall["hall_id"], date, session) not in unavailable
            ]
            bins, unplaced = _allocate_session(self.data, session_assignments, available_halls)

            for item in unplaced:
                self.violations.append({
                    "rule_id": "BR-05",
                    "severity": "HARD",
                    "entity": item["code"],
                    "message": (
                        f"{item['count']} students in {item['code']} could not be assigned "
                        f"to a compatible hall for {date} {session}; check capacity, "
                        "duration, department-mixing, small-course merging and special-needs constraints"
                    ),
                })

            for bin_data in bins:
                if not bin_data["courses"]:
                    continue
                extended_end = None
                if bin_data["special"]:
                    window = next((row for row in self.data["exam_window"]
                        if row["date"] == date and row["session"] == session), None)
                    if window and window.get("end_time"):
                        from datetime import datetime, timedelta
                        end = datetime.strptime(window["end_time"], "%H:%M") + timedelta(minutes=20)
                        extended_end = end.strftime("%H:%M")
                result.append(HallAssignment(
                    date=date,
                    session=session,
                    hall_id=bin_data["hall"]["hall_id"],
                    courses=list(bin_data["courses"]),
                    students=list(bin_data["students"]),
                    duration=int(bin_data["duration"]),
                    extended_end=extended_end,
                ))

        return result
