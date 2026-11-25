import csv
import os

class DataLoader:
    """Loads PS-067 CSV inputs and builds indexed in-memory data."""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.data = {}

    def _read(self, filename, required=True):
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            if required:
                raise FileNotFoundError(f"Required input file not found: {path}")
            return []
        with open(path, newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def load_all(self):
        names = {
            "courses": "courses.csv",
            "students": "students.csv",
            "enrolments": "enrolments.csv",
            "halls": "halls.csv",
            "invigilators": "invigilators.csv",
            "exam_window": "exam_window.csv",
            "holidays": "holidays.csv",
        }
        for key, filename in names.items():
            self.data[key] = self._read(filename)
        self.data["late_students"] = self._read("late_students.csv", False)
        self.data["late_enrolments"] = self._read("late_enrolments.csv", False)
        self.data["change_commands"] = self._read("change_commands.csv", False)
        self._build_indexes()
        return self.data

    def _build_indexes(self):
        courses = {r["course_code"]: r for r in self.data["courses"]}
        students = {r["student_id"]: r for r in self.data["students"]}
        course_students = {code: [] for code in courses}
        student_courses = {sid: [] for sid in students}
        for row in self.data["enrolments"]:
            code, sid = row["course_code"], row["student_id"]
            if code in course_students and sid in student_courses:
                course_students[code].append(sid)
                student_courses[sid].append(code)
        for code, course in courses.items():
            course["enrolment_count"] = str(len(course_students[code]))
        self.data.update({
            "course_by_code": courses,
            "student_by_id": students,
            "course_students": course_students,
            "student_courses": student_courses,
            "hall_by_id": {r["hall_id"]: r for r in self.data["halls"]},
            "invigilator_by_id": {r["invigilator_id"]: r for r in self.data["invigilators"]},
        })
