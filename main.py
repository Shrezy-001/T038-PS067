import argparse
import csv
import os
import sys

from engine.data_loader import DataLoader
from engine.validator import DataValidator
from engine.scheduler import ExamScheduler
from engine.hall_allocator import HallAllocator
from engine.seating_engine import SeatingEngine
from engine.invigilator_allocator import InvigilatorAllocator
from engine.change_manager import ChangeManager
from commands.command_processor import CommandProcessor
from reports.timetable_report import TimetableReport
from reports.hall_report import HallReport
from reports.invigilation_report import InvigilationReport
from reports.violation_report import ViolationReport


def planned_hall_closures(command_path, data):
    """Read planned hall closures before scheduling so session packing is feasible."""
    closures = set()
    if not command_path or not os.path.isfile(command_path):
        return closures
    with open(command_path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        if row.get("command", "").strip().upper() != "HALL_UNAVAILABLE":
            continue
        hall_id = row.get("target", "").strip()
        parts = row.get("parameter", "").split("|")
        date = parts[0].strip() if parts else ""
        session = parts[1].strip().upper() if len(parts) > 1 else "ALL"
        sessions = {
            r["session"] for r in data["exam_window"]
            if r["date"] == date
            and str(r.get("available", "")).strip().upper() in ("YES", "TRUE", "1")
        } if session == "ALL" else {session}
        for value in sessions:
            closures.add((hall_id, date, value))
    return closures


def run(data_dir="data", output_dir="output", command_file=None):
    print("PS-067 University Exam Timetabling and Hall Allocation Engine")
    print("-" * 65)
    data = DataLoader(data_dir).load_all()
    validation = DataValidator().validate(data)
    if not validation["valid"]:
        print("Input validation failed:")
        for error in validation["errors"]:
            print(f"  - {error}")
        return 2

    print(
        f"Loaded {len(data['courses'])} courses, {len(data['students'])} students, "
        f"{len(data['halls'])} halls and {len(data['invigilators'])} invigilators."
    )

    commands_path = command_file or os.path.join(data_dir, "change_commands.csv")
    unavailable = planned_hall_closures(commands_path, data)
    scheduler = ExamScheduler(data, unavailable_halls=unavailable)
    assignments = scheduler.generate()
    print(f"Scheduled {len(assignments)} of {len(data['courses'])} courses.")

    hall_allocator = HallAllocator(data)
    hall_assignments = hall_allocator.allocate(assignments, unavailable=unavailable)
    seating_plan = SeatingEngine(data).create_seating_plan(hall_assignments)
    roster = InvigilatorAllocator(data).allocate(hall_assignments)

    violations = list(scheduler.violations) + list(hall_allocator.violations)

    change_manager = ChangeManager(
        data, assignments, hall_assignments, roster,
        unavailable_halls=unavailable
    )
    if commands_path and os.path.isfile(commands_path):
        processor = CommandProcessor(change_manager, data, data_dir)
        results = processor.process_file(commands_path)
        os.makedirs(output_dir, exist_ok=True)
        processor.write_results(os.path.join(output_dir, "command_results.csv"))
        print(f"Processed {len(results)} change commands.")
        hall_assignments = change_manager.hall_assignments
        roster = change_manager.roster
        seating_plan = SeatingEngine(data).create_seating_plan(hall_assignments)
        violations.extend(change_manager.violations)

    os.makedirs(output_dir, exist_ok=True)
    TimetableReport(output_dir).generate(assignments, data)
    HallReport(output_dir).generate(hall_assignments, seating_plan, data)
    InvigilationReport(output_dir).generate(roster, data)
    ViolationReport(output_dir).generate(violations)
    print(f"Reports written to: {os.path.abspath(output_dir)}")
    print("Run completed.")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data")
    parser.add_argument("--output", default="output")
    parser.add_argument("--commands", default=None)
    args = parser.parse_args()
    try:
        return run(args.data, args.output, args.commands)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
