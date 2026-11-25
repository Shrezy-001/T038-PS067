from datetime import datetime

class DataValidator:
    def validate(self, data):
        errors = []
        warnings = []
        self._unique(data["courses"], "course_code", "courses", errors)
        self._unique(data["students"], "student_id", "students", errors)
        self._unique(data["halls"], "hall_id", "halls", errors)
        self._unique(data["invigilators"], "invigilator_id", "invigilators", errors)

        course_codes = set(data["course_by_code"])
        student_ids = set(data["student_by_id"])
        for i, row in enumerate(data["enrolments"], 2):
            if row["course_code"] not in course_codes:
                errors.append(f"enrolments.csv row {i}: unknown course {row['course_code']}")
            if row["student_id"] not in student_ids:
                errors.append(f"enrolments.csv row {i}: unknown student {row['student_id']}")

        for course in data["courses"]:
            try:
                duration = int(course["exam_duration_hours"])
                if duration not in (2, 3):
                    errors.append(f"{course['course_code']}: duration must be 2 or 3")
            except (ValueError, KeyError):
                errors.append(f"{course.get('course_code', '?')}: invalid exam duration")

        for hall in data["halls"]:
            try:
                if int(hall["capacity"]) <= 0:
                    errors.append(f"{hall['hall_id']}: capacity must be positive")
            except (ValueError, KeyError):
                errors.append(f"{hall.get('hall_id', '?')}: invalid capacity")

        for row in data["exam_window"]:
            try:
                datetime.strptime(row["date"], "%Y-%m-%d")
                if row["session"] not in ("FN", "AN"):
                    errors.append(f"Invalid session {row['session']} on {row['date']}")
            except ValueError:
                errors.append(f"Invalid exam-window date: {row.get('date')}")

        return {"valid": not errors, "errors": errors, "warnings": warnings}

    @staticmethod
    def _unique(rows, field, label, errors):
        seen = set()
        for row in rows:
            value = row.get(field)
            if not value:
                errors.append(f"{label}: missing {field}")
            elif value in seen:
                errors.append(f"{label}: duplicate {field} {value}")
            seen.add(value)
