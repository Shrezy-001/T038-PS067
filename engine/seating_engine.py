class SeatingEngine:
    """Builds deterministic row-major seating plans for each allocated hall.

    For a merged two-course hall, the first course uses odd-numbered columns
    and the second course uses even-numbered columns. This interleaves the two
    courses without placing students from the same course in adjacent columns.
    In a single-course hall, all columns remain available.

    Special-needs students are placed first in row 1, and only in ground-floor
    halls. Within the special-needs and regular groups, register-number order
    is preserved.
    """

    def __init__(self, data):
        self.data = data

    def _register_key(self, student_id):
        student = self.data["student_by_id"].get(student_id, {})
        return str(student.get("register_number", student_id)).strip().upper()

    def create_seating_plan(self, hall_assignments):
        plans = []
        course_students = self.data.get("course_students", {})

        for ha in hall_assignments:
            hall = self.data["hall_by_id"][ha.hall_id]
            rows = int(hall["rows"])
            cols = int(hall["columns"])
            is_ground = str(hall.get("floor", "")).strip().upper() == "GROUND"
            courses = list(ha.courses)

            if len(courses) == 2:
                course_columns = {
                    courses[0]: list(range(1, cols + 1, 2)),
                    courses[1]: list(range(2, cols + 1, 2)),
                }
            elif len(courses) == 1:
                course_columns = {courses[0]: list(range(1, cols + 1, 2))}
            else:
                course_columns = {
                    code: list(range(1, cols + 1)) for code in courses
                }

            for course_code in courses:
                enrolled = set(course_students.get(course_code, []))
                students = [sid for sid in ha.students if sid in enrolled]
                students.sort(key=self._register_key)
                special = [
                    sid for sid in students
                    if str(self.data["student_by_id"].get(sid, {}).get("special_needs", "NO")).strip().upper() == "YES"
                ]
                regular = [sid for sid in students if sid not in set(special)]
                columns = course_columns.get(course_code, list(range(1, cols + 1)))

                # Seat coordinates are row-major within the course's assigned
                # columns, while the reported seat number remains the hall's
                # physical row-major seat number.
                row_one_seats = [(1, col) for col in columns]
                remaining_seats = [
                    (row, col)
                    for row in range(1, rows + 1)
                    for col in columns
                    if (row, col) not in row_one_seats[:len(special)]
                ]

                special_seated = []
                if is_ground:
                    special_seated = special[:len(row_one_seats)]
                    for sid, (row, col) in zip(special_seated, row_one_seats):
                        plans.append(self._seat_record(ha, sid, course_code, row, col, cols, "YES", "GROUND_ROW_1", "ASSIGNED"))
                    for sid in special[len(row_one_seats):]:
                        plans.append(self._seat_record(ha, sid, course_code, "", "", cols, "YES", "NO", "SPECIAL_ROW_CAPACITY_EXCEEDED"))
                else:
                    for sid in special:
                        plans.append(self._seat_record(ha, sid, course_code, "", "", cols, "YES", "NO", "SPECIAL_NEEDS_REQUIRES_GROUND_FLOOR"))

                # Non-special students use all remaining positions in register
                # number order. If the hall cannot seat them, retain an explicit
                # unseated record rather than silently dropping a student.
                available = remaining_seats if is_ground else [
                    (row, col)
                    for row in range(1, rows + 1)
                    for col in columns
                ]
                for sid, (row, col) in zip(regular, available):
                    plans.append(self._seat_record(ha, sid, course_code, row, col, cols, "NO", "NO", "ASSIGNED"))
                for sid in regular[len(available):]:
                    plans.append(self._seat_record(ha, sid, course_code, "", "", cols, "NO", "NO", "CAPACITY_EXCEEDED"))

        return plans

    @staticmethod
    def _seat_record(ha, sid, course_code, row, col, cols, special, priority, status):
        seat_number = (row - 1) * cols + col if isinstance(row, int) and isinstance(col, int) else ""
        return {
            "date": ha.date,
            "session": ha.session,
            "hall_id": ha.hall_id,
            "course_code": course_code,
            "student_id": sid,
            "row": row,
            "column": col,
            "seat_number": seat_number,
            "special_needs": special,
            "priority_seating": priority,
            "status": status,
        }
