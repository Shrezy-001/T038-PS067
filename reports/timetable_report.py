from .base_report import BaseReport

class TimetableReport(BaseReport):
    FIELDS = ["course_code", "date", "session", "start_time", "end_time",
              "duration_hours", "enrolment_count", "status", "soft_violations"]

    def generate(self, assignments, data):
        window = {(r["date"], r["session"]): r for r in data["exam_window"]}
        courses = data["course_by_code"]
        rows = []
        for a in sorted(assignments, key=lambda x:(x.date, 0 if x.session=="FN" else 1, x.course_code)):
            slot = window.get((a.date, a.session), {})
            rows.append({
                "course_code": a.course_code,
                "date": a.date,
                "session": a.session,
                "start_time": slot.get("start_time", ""),
                "end_time": slot.get("end_time", ""),
                "duration_hours": a.duration,
                "enrolment_count": len(a.students),
                "status": "SCHEDULED",
                "soft_violations": " | ".join(a.soft_violations)
            })
        path = self.write_csv("timetable.csv", rows, self.FIELDS)
        lines = ["UNIVERSITY EXAMINATION TIMETABLE", "=" * 70, ""]
        for r in rows:
            lines.append(
                f'{r["date"]} {r["session"]} ({r["start_time"]}-{r["end_time"]}) | '
                f'{r["course_code"]:<12} | {r["enrolment_count"]:>4} students | '
                f'{r["duration_hours"]} hours'
            )
            if r["soft_violations"]:
                lines.append(f'  SOFT VIOLATION: {r["soft_violations"]}')
        self.write_text("timetable.txt", "\n".join(lines) + "\n")
        return path
