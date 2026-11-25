from collections import defaultdict
from datetime import date
from math import ceil


class InvigilatorAllocator:
    """Allocate chiefs before ordinary invigilators while respecting all loads."""

    def __init__(self, data):
        self.data = data
        self.violations = []

    @staticmethod
    def _week_key(date_text):
        parsed = date.fromisoformat(date_text)
        iso = parsed.isocalendar()
        return (iso.year, iso.week)

    def allocate(self, hall_assignments):
        keys = {(ha.date, ha.session) for ha in hall_assignments}
        return self.allocate_incremental(hall_assignments, [], keys)

    def allocate_incremental(self, hall_assignments, existing_roster, affected_sessions):
        self.violations = []
        affected_sessions = set(affected_sessions)
        preserved = [
            row for row in existing_roster
            if (row.get("date"), row.get("session")) not in affected_sessions
        ]
        weekly = defaultdict(int)
        daily = defaultdict(int)
        session = defaultdict(int)
        total = defaultdict(int)
        inv_by_id = {x["invigilator_id"]: x for x in self.data["invigilators"]}

        def add_load(iid, day, sess):
            weekly[(iid, self._week_key(day))] += 1
            daily[(iid, day)] += 1
            session[(iid, day, sess)] += 1
            total[iid] += 1

        for row in preserved:
            iid = row["invigilator_id"]
            if iid in inv_by_id:
                add_load(iid, row["date"], row["session"])

        halls = [h for h in hall_assignments if (h.date, h.session) in affected_sessions]
        halls.sort(key=lambda h: (h.date, h.session, h.hall_id))
        groups = defaultdict(list)
        for h in halls:
            building = self.data["hall_by_id"][h.hall_id]["building"]
            groups[(h.date, h.session, building)].append(h)

        new_rows = []

        def available(inv, day, sess, departments, chief=False):
            iid = inv["invigilator_id"]
            unavailable = {v.strip() for v in inv.get("unavailable_dates", "").split(";") if v.strip()}
            if inv["department"] in departments or day in unavailable:
                return False
            if chief and str(inv.get("is_chief_eligible", "NO")).strip().upper() != "YES":
                return False
            if daily[(iid, day)] >= 2 or session[(iid, day, sess)] > 0:
                return False
            if weekly[(iid, self._week_key(day))] >= int(inv["max_sessions_per_week"]):
                return False
            return True

        # Reserve one chief for each building/session before ordinary hall staffing.
        for (day, sess, building), group_halls in sorted(groups.items()):
            departments = {
                self.data["course_by_code"][code]["department"]
                for h in group_halls for code in h.courses
            }
            candidates = [i for i in self.data["invigilators"]
                          if available(i, day, sess, departments, chief=True)]
            candidates.sort(key=lambda i: (total[i["invigilator_id"]], i["department"], i["invigilator_id"]))
            if candidates:
                inv = candidates[0]
                iid = inv["invigilator_id"]
                chief_hall = min(group_halls, key=lambda h: h.hall_id)
                new_rows.append({"date": day, "session": sess, "hall_id": chief_hall.hall_id,
                                 "invigilator_id": iid, "role": "CHIEF", "status": "ASSIGNED"})
                add_load(iid, day, sess)
            else:
                self.violations.append({
                    "rule_id": "BR-08", "severity": "HARD", "entity": building,
                    "message": "UNSTAFFED: no eligible chief available after department, availability and workload checks"
                })

        # Assign ordinary invigilators after chief reservations.
        for h in halls:
            required = max(1, ceil(len(h.students) / 30))
            departments = {self.data["course_by_code"][code]["department"] for code in h.courses}
            candidates = [i for i in self.data["invigilators"]
                          if available(i, h.date, h.session, departments)]
            candidates.sort(key=lambda i: (total[i["invigilator_id"]], i["department"], i["invigilator_id"]))
            selected = candidates[:required]
            for inv in selected:
                iid = inv["invigilator_id"]
                new_rows.append({"date": h.date, "session": h.session, "hall_id": h.hall_id,
                                 "invigilator_id": iid, "role": "INVIGILATOR", "status": "ASSIGNED"})
                add_load(iid, h.date, h.session)
            if len(selected) < required:
                self.violations.append({
                    "rule_id": "BR-07", "severity": "HARD", "entity": h.hall_id,
                    "message": f"UNSTAFFED: required {required}, assigned {len(selected)}"
                })
        return preserved + new_rows
