import csv
import json
import os

class CommandProcessor:
    """Reads and executes PS-067 change commands in sequence."""

    SUPPORTED = {
        "POSTPONE",
        "HALL_UNAVAILABLE",
        "ADD_LATE_REGISTRANT",
    }

    def __init__(self, change_manager, data, data_dir=None):
        self.change_manager = change_manager
        self.data = data
        self.data_dir = data_dir
        self.results = []

    def process_file(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Command file not found: {path}")

        with open(path, newline="", encoding="utf-8-sig") as f:
            commands = list(csv.DictReader(f))

        commands.sort(key=lambda row: int(row.get("sequence", 0)))
        for command in commands:
            self.results.append(self.process(command))
        return self.results

    def process(self, command):
        name = command.get("command", "").strip().upper()
        target = command.get("target", "").strip()
        parameter = command.get("parameter", "").strip()
        sequence = command.get("sequence", "")

        if name not in self.SUPPORTED:
            return self._result(sequence, name, target, "REJECTED_UNKNOWN_COMMAND",
                                f"Unsupported command: {name}")

        try:
            if name == "POSTPONE":
                parts = parameter.split("|")
                target_date = parts[0].strip() if parts and parts[0].strip() else None
                target_session = parts[1].strip().upper() if len(parts) > 1 and parts[1].strip() else None
                result = self.change_manager.postpone(target, target_date, target_session)

            elif name == "HALL_UNAVAILABLE":
                parts = parameter.split("|")
                unavailable_date = parts[0].strip() if parts else ""
                session = parts[1].strip().upper() if len(parts) > 1 and parts[1].strip() else "ALL"
                result = self.change_manager.mark_hall_unavailable(target, unavailable_date, session)

            else:  # ADD_LATE_REGISTRANT
                student = self.data.get("student_by_id", {}).get(target)
                if student is None:
                    student = next(
                        (s for s in self.data.get("late_students", [])
                         if s.get("student_id") == target),
                        None
                    )
                if student is None:
                    result = {"status": "REJECTED_UNKNOWN_STUDENT", "student_id": target}
                else:
                    result = self.change_manager.add_late_registrant(student, parameter)

            return self._result(sequence, name, target, result.get("status", "PROCESSED"),
                                json.dumps(result, sort_keys=True), result)

        except (ValueError, KeyError, IndexError) as exc:
            return self._result(sequence, name, target, "REJECTED_INVALID_COMMAND", str(exc))

    @staticmethod
    def _result(sequence, command, target, status, message, details=None):
        return {
            "sequence": sequence,
            "command": command,
            "target": target,
            "status": status,
            "message": message,
            "details": details or {}
        }

    def write_results(self, output_path):
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        fields = ["sequence", "command", "target", "status", "message"]
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in self.results:
                writer.writerow({key: row.get(key, "") for key in fields})
        return output_path
