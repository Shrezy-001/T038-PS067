from .base_report import BaseReport

class ViolationReport(BaseReport):
    FIELDS = ["rule_id", "severity", "entity", "message"]

    def generate(self, violations):
        normalized = []
        for v in violations:
            if hasattr(v, "__dict__"):
                row = v.__dict__.copy()
            else:
                row = dict(v)
            normalized.append({
                "rule_id": row.get("rule_id", "UNKNOWN"),
                "severity": row.get("severity", "INFO"),
                "entity": row.get("entity", ""),
                "message": row.get("message", "")
            })
        normalized.sort(key=lambda x:(
            {"HARD":0,"SOFT":1,"WARNING":2,"INFO":3}.get(x["severity"],4),
            x["rule_id"], x["entity"], x["message"]
        ))
        path = self.write_csv("violations.csv", normalized, self.FIELDS)
        counts = {}
        for r in normalized:
            counts[r["severity"]] = counts.get(r["severity"], 0) + 1
        lines = ["VIOLATIONS REPORT", "=" * 70, ""]
        lines.append(f"Total violations: {len(normalized)}")
        for severity in ("HARD", "SOFT", "WARNING", "INFO"):
            lines.append(f"{severity}: {counts.get(severity, 0)}")
        lines.append("")
        if not normalized:
            lines.append("No violations recorded.")
        else:
            for r in normalized:
                lines.append(f'[{r["severity"]}] {r["rule_id"]} | {r["entity"]}')
                lines.append(f'  {r["message"]}')
        self.write_text("violations.txt", "\n".join(lines) + "\n")
        return path
