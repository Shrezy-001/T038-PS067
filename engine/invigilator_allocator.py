from collections import defaultdict
from datetime import date
from math import ceil


class InvigilatorAllocator:
    """Allocates invigilators with workload accounting and incremental rebuilds."""

    def __init__(self, data):
        self.data = data
        self.violations = []

    @staticmethod
    def _week_key(date_text):
        parsed = date.fromisoformat(date_text)
        iso = parsed.isocalendar()
        return (iso.year, iso.week)

    def allocate(self, hall_assignments):
        all_keys = {(ha.date, ha.session) for ha in hall_assignments}
        return self.allocate_incremental(hall_assignments, [], all_keys)

    def allocate_incremental(self, hall_assignments, existing_roster, affected_sessions):
        self.violations = []
        affected_sessions = set(affected_sessions)
        preserved = [
            row for row in existing_roster
            if (row.get("date"), row.get("session")) not in affected_sessions
        ]

        weekly_load = defaultdict(int)
        daily_load = defaultdict(int)
        session_load = defaultdict(int)
        assigned_total = defaultdict(int)

        inv_by_id = {
            inv["invigilator_id"]: inv for inv in self.data["invigilators"]
        }

        for row in preserved:
            iid = row["invigilator_id"]
            if iid not in inv_by_id:
                continue
            weekly_load[(iid, self._week_key(row["date"]))] += 1
            daily_load[(iid, row["date"])] += 1
            session_load[(iid, row["date"], row["session"])] += 1
            assigned_total[iid] += 1

        affected_halls = [
            ha for ha in hall_assignments
            if (ha.date, ha.session) in affected_sessions
        ]
        affected_halls.sort(key=lambda ha: (ha.date, ha.session, ha.hall_id))

        new_rows = []
        for ha in affected_halls:
            hall = self.data["hall_by_id"][ha.hall_id]
            required = max(1, ceil(len(ha.students) / 30))
            course_departments = {
                self.data["course_by_code"][code]["department"]
                for code in ha.courses
            }
            eligible = []

            for inv in self.data["invigilators"]:
                iid = inv["invigilator_id"]
                unavailable = {
                    value.strip()
                    for value in inv.get("unavailable_dates", "").split(";")
                    if value.strip()
                }
                week = self._week_key(ha.date)
                if inv["department"] in course_departments:
                    continue
                if ha.date in unavailable:
                    continue
                if daily_load[(iid, ha.date)] >= 2:
                    continue
                if session_load[(iid, ha.date, ha.session)]:
                    continue
                if weekly_load[(iid, week)] >= int(inv["max_sessions_per_week"]):
                    continue
                eligible.append(inv)

            eligible.sort(key=lambda inv: (
                assigned_total[inv["invigilator_id"]],
                inv["department"],
                inv["invigilator_id"],
            ))
            selected = eligible[:required]

            for inv in selected:
                iid = inv["invigilator_id"]
                new_rows.append({
                    "date": ha.date,
                    "session": ha.session,
                    "hall_id": ha.hall_id,
                    "invigilator_id": iid,
                    "role": "INVIGILATOR",
                    "status": "ASSIGNED",
                })
                weekly_load[(iid, self._week_key(ha.date))] += 1
                daily_load[(iid, ha.date)] += 1
                session_load[(iid, ha.date, ha.session)] += 1
                assigned_total[iid] += 1

            if len(selected) < required:
                self.violations.append({
                    "rule_id": "BR-10/11",
                    "severity": "HARD",
                    "entity": ha.hall_id,
                    "message": (
                        f"UNSTAFFED: required {required}, assigned {len(selected)}"
                    ),
                })

        # One chief per building/session. Check all course departments in that
        # building/session, not just the first hall encountered.
        building_groups = defaultdict(list)
        for ha in affected_halls:
            building = self.data["hall_by_id"][ha.hall_id]["building"]
            building_groups[(ha.date, ha.session, building)].append(ha)

        for (exam_date, session, building), halls in sorted(building_groups.items()):
            building_departments = {
                self.data["course_by_code"][code]["department"]
                for ha in halls for code in ha.courses
            }
            candidates = []

            for inv in self.data["invigilators"]:
                iid = inv["invigilator_id"]
                unavailable = {
                    value.strip()
                    for value in inv.get("unavailable_dates", "").split(";")
                    if value.strip()
                }
                if str(inv.get("is_chief_eligible", "NO")).upper() != "YES":
                    continue
                if inv["department"] in building_departments or exam_date in unavailable:
                    continue
                if daily_load[(iid, exam_date)] >= 2:
                    continue
                if session_load[(iid, exam_date, session)]:
                    continue
                if weekly_load[(iid, self._week_key(exam_date))] >= int(inv["max_sessions_per_week"]):
                    continue
                candidates.append(inv)

            candidates.sort(key=lambda inv: (
                assigned_total[inv["invigilator_id"]],
                inv["department"],
                inv["invigilator_id"],
            ))

            if candidates:
                inv = candidates[0]
                iid = inv["invigilator_id"]
                # Attach the chief to the first hall in the building.
                chief_hall = sorted(halls, key=lambda ha: ha.hall_id)[0]
                new_rows.append({
                    "date": exam_date,
                    "session": session,
                    "hall_id": chief_hall.hall_id,
                    "invigilator_id": iid,
                    "role": "CHIEF",
                    "status": "ASSIGNED",
                })
                weekly_load[(iid, self._week_key(exam_date))] += 1
                daily_load[(iid, exam_date)] += 1
                session_load[(iid, exam_date, session)] += 1
                assigned_total[iid] += 1
            else:
                self.violations.append({
                    "rule_id": "BR-10/11",
                    "severity": "HARD",
                    "entity": building,
                    "message": "UNSTAFFED: no eligible chief available",
                })

        return preserved + new_rows
