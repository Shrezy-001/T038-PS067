from .models import Violation

class ViolationManager:
    def __init__(self):
        self.items = []

    def add(self, rule_id, severity, entity, message):
        self.items.append(Violation(rule_id, severity, entity, message))

    def extend(self, violations):
        for v in violations:
            if isinstance(v, Violation):
                self.items.append(v)
            else:
                self.add(v.get("rule_id","UNKNOWN"),v.get("severity","INFO"),
                         v.get("entity",""),v.get("message",""))

    def as_dicts(self):
        return [v.__dict__.copy() for v in self.items]
