from .base_report import BaseReport

class InvigilationReport(BaseReport):
    FIELDS = ["date", "session", "hall_id", "invigilator_id", "invigilator_name",
              "department", "role", "status"]

    def generate(self, roster, data):
        rows = []
        for r in sorted(roster, key=lambda x:(x["date"], 0 if x["session"]=="FN" else 1,
                                               x["hall_id"], x["role"], x["invigilator_id"])):
            inv = data["invigilator_by_id"].get(r["invigilator_id"], {})
            rows.append({
                **r,
                "invigilator_name": inv.get("name", ""),
                "department": inv.get("department", "")
            })
        path = self.write_csv("invigilation_roster.csv", rows, self.FIELDS)
        lines = ["INVIGILATION DUTY ROSTER", "=" * 70, ""]
        for r in rows:
            lines.append(
                f'{r["date"]} {r["session"]} | Hall {r["hall_id"]} | '
                f'{r["role"]:<12} | {r["invigilator_id"]} '
                f'{r["invigilator_name"]} ({r["department"]})'
            )
        self.write_text("invigilation_roster.txt", "\n".join(lines) + "\n")
        return path
