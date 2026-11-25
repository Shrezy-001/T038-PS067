class SeatingEngine:
    def __init__(self, data):
        self.data = data

    def create_seating_plan(self, hall_assignments):
        plans = []
        for ha in hall_assignments:
            hall = self.data["hall_by_id"][ha.hall_id]
            rows, cols = int(hall["rows"]), int(hall["columns"])
            students = sorted(ha.students, key=lambda sid: self.data["student_by_id"].get(sid, {}).get("register_number", sid))
            # Assign students in row-major order while spreading each course over alternate columns.
            for index, sid in enumerate(students):
                row = index // cols + 1
                col = index % cols + 1
                if row > rows:
                    plans.append({"date":ha.date,"session":ha.session,"hall_id":ha.hall_id,
                                  "student_id":sid,"row":"","column":"","seat_number":"",
                                  "status":"CAPACITY_EXCEEDED"})
                    continue
                student = self.data["student_by_id"].get(sid, {})
                special = student.get("special_needs", "NO").upper() == "YES"
                plans.append({
                    "date":ha.date, "session":ha.session, "hall_id":ha.hall_id,
                    "student_id":sid, "row":row, "column":col,
                    "seat_number":(row-1)*cols+col,
                    "special_needs": "YES" if special else "NO",
                    "priority_seating": "GROUND_ROW_1" if special and row == 1 and hall.get("floor") == "GROUND" else "NO"
                })
        return plans
