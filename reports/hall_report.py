from .base_report import BaseReport
import os

class HallReport(BaseReport):
    ALLOCATION_FIELDS = ["date", "session", "hall_id", "building", "capacity",
                         "course_codes", "student_count", "duration_hours", "extended_end"]
    SEATING_FIELDS = ["date", "session", "hall_id", "course_code", "student_id", "register_number",
                      "student_name", "row", "column", "seat_number",
                      "special_needs", "priority_seating", "status"]

    def generate(self, hall_assignments, seating_plan, data):
        allocations = []
        for ha in sorted(hall_assignments, key=lambda x:(x.date, 0 if x.session=="FN" else 1, x.hall_id)):
            hall = data["hall_by_id"][ha.hall_id]
            allocations.append({
                "date": ha.date, "session": ha.session, "hall_id": ha.hall_id,
                "building": hall.get("building", ""),
                "capacity": hall.get("capacity", ""),
                "course_codes": ";".join(ha.courses),
                "student_count": len(ha.students),
                "duration_hours": ha.duration,
                "extended_end": ha.extended_end or ""
            })
        self.write_csv("hall_allocation.csv", allocations, self.ALLOCATION_FIELDS)

        seats = []
        for p in seating_plan:
            student = data["student_by_id"].get(p["student_id"], {})
            seats.append({
                **p,
                "register_number": student.get("register_number", p["student_id"]),
                "student_name": student.get("name", "")
            })
        seats.sort(key=lambda x:(x["date"], x["session"], x["hall_id"],
                                 int(x["row"]) if str(x["row"]).isdigit() else 9999,
                                 int(x["column"]) if str(x["column"]).isdigit() else 9999))
        self.write_csv("seating_plan.csv", seats, self.SEATING_FIELDS)

        # Human-readable seat map grouped by hall/session.
        grouped = {}
        for p in seats:
            key = (p["date"], p["session"], p["hall_id"])
            grouped.setdefault(key, []).append(p)
        lines = ["EXAMINATION HALL SEATING MAP", "=" * 70, ""]
        for (date, session, hall_id), items in sorted(grouped.items()):
            lines.append(f"{date} {session} | {hall_id}")
            lines.append("-" * 50)
            valid = [p for p in items if str(p["row"]).isdigit() and str(p["column"]).isdigit()]
            by_row = {}
            for p in valid:
                by_row.setdefault(int(p["row"]), []).append(p)
            for row_num in sorted(by_row):
                row_items = sorted(by_row[row_num], key=lambda x:int(x["column"]))
                cells = [f'C{p["column"]}:{p["register_number"]}' for p in row_items]
                lines.append(f'R{row_num}: ' + " | ".join(cells))
            lines.append("")
        self.write_text("seating_map.txt", "\n".join(lines))
        return os.path.join(self.output_dir, "hall_allocation.csv")
