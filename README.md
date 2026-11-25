# PS-067 — University Exam Timetabling and Hall Allocation Engine

A command-file-driven Python backend for planning university end-semester examinations. The engine reads course, student, enrolment, examination-window, hall and invigilator data from CSV files; creates an examination timetable; allocates halls and seats; assigns invigilators; processes selected schedule changes; and writes machine-readable and human-readable reports.

> **Project ID:** PS-067  
> **Domain:** Education — University Examinations  
> **Difficulty:** High  
> **Language:** Python 3.10+  
> **Interface:** Command-line / CSV driven (no graphical user interface)

---

## Table of contents

1. [Problem statement](#1-problem-statement)
2. [Project goals](#2-project-goals)
3. [System workflow](#3-system-workflow)
4. [Architecture](#4-architecture)
5. [Scheduling algorithm](#5-scheduling-algorithm)
6. [Business-rule mapping](#6-business-rule-mapping)
7. [Hall allocation and seating](#7-hall-allocation-and-seating)
8. [Invigilator allocation](#8-invigilator-allocation)
9. [Change-command processing](#9-change-command-processing)
10. [Input data files](#10-input-data-files)
11. [Generated output files](#11-generated-output-files)
12. [Installation and execution](#12-installation-and-execution)
13. [Command-file format](#13-command-file-format)
14. [Validation and error handling](#14-validation-and-error-handling)
15. [Project directory structure](#15-project-directory-structure)
16. [Implementation notes and limitations](#16-implementation-notes-and-limitations)
17. [Evaluation dataset](#17-evaluation-dataset)

---

## 1. Problem statement

University examination sections must schedule many courses across a fixed examination window while coordinating student availability, hall capacity, seating arrangements and invigilator workloads. Manual planning can create timetable clashes, unfair examination spacing, over-capacity halls, invalid staff assignments and expensive rework when a course is postponed or a hall becomes unavailable.

PS-067 implements a backend engine to automate these tasks. It accepts structured CSV input and an ordered command file, then produces the timetable, hall plan, seating plan, invigilation roster and violation reports.

The supplied problem statement defines the principal scale as 120 courses, 2,500 students, 18 halls, 90 invigilators and a 12-day examination window. The local sample data should be treated as the actual source of records for a particular run; the engine reports the counts it loads at runtime.

## 2. Project goals

- Generate a timetable for registered courses using available FN and AN examination sessions.
- Avoid two examinations for the same student in the same session.
- Enforce the daily examination rule and backlog-consent exception represented in the input data.
- Apply the programme-semester core-course gap check.
- Respect the 90% aggregate available-hall capacity limit and hall duration compatibility.
- Allocate students to halls and produce physical seat coordinates and seat numbers.
- Accommodate special-needs students using ground-floor halls and extended hall end times where configured by the implementation.
- Assign invigilators while checking department conflicts, unavailable dates and workload limits.
- Process postponement, hall-unavailability and late-registration commands.
- Preserve assignments outside the sessions selected for incremental rebuilding.
- Generate CSV and text reports for review and downstream processing.

## 3. System workflow

The normal execution follows this sequence:

1. **Load input:** `DataLoader` reads the required CSV files and optional late-registration and command files.
2. **Build indexes:** The loader creates lookups such as course-by-code, student-by-ID, hall-by-ID, invigilator-by-ID, course-to-students and student-to-courses.
3. **Validate input:** `DataValidator` checks duplicate identifiers, enrolment references, exam durations, hall capacities, dates and session names.
4. **Schedule courses:** `ExamScheduler` orders courses and places each in the earliest feasible available session, using the constraint checker and capacity/hall-packing checks.
5. **Allocate halls:** `HallAllocator` packs the courses assigned to each session into compatible halls.
6. **Create seating plan:** `SeatingEngine` assigns student seat coordinates and physical row-major seat numbers.
7. **Allocate invigilators:** `InvigilatorAllocator` reserves chief assignments by building/session and then assigns ordinary invigilators to halls.
8. **Process changes:** `CommandProcessor` reads commands in sequence and calls `ChangeManager` to apply supported changes.
9. **Rebuild affected sessions:** When a supported change affects a session, the change manager regenerates hall and roster assignments for the affected session set while retaining other session rows.
10. **Write reports:** Report classes write CSV and text output under the output directory.

## 4. Architecture

The code is separated into five main areas:

| Area | Responsibility |
|---|---|
| `main.py` | Coordinates loading, validation, scheduling, allocation, changes and reporting. |
| `data/` | CSV input datasets and data-format notes. |
| `engine/` | Scheduling, constraints, allocation, seating, validation and change-management logic. |
| `commands/` | Parses and executes the ordered change-command file. |
| `reports/` | Produces timetable, hall, invigilation and violation reports. |

### Main engine modules

- **`data_loader.py`** — Reads CSV inputs and builds in-memory indexes used by the other modules.
- **`validator.py`** — Checks input consistency before the scheduling process starts.
- **`models.py`** — Defines the `Assignment`, `HallAssignment` and `Violation` data structures.
- **`ordering_heuristic.py`** — Provides deterministic course ordering.
- **`constraint_checker.py`** — Checks student session clashes, daily examination limits, backlog-consent conditions and core-course gaps.
- **`scheduler.py`** — Generates course-to-session assignments and records courses that cannot be placed.
- **`hall_allocator.py`** — Packs compatible courses into halls and checks hall/session capacity constraints.
- **`seating_engine.py`** — Produces student-level seat assignments.
- **`invigilator_allocator.py`** — Assigns chief and ordinary invigilators while accounting for workload.
- **`incremental_scheduler.py`** — Identifies the old and new sessions affected by a changed assignment.
- **`change_manager.py`** — Applies postponements, hall closures and late registrations and rebuilds affected allocations.
- **`violation_manager.py`** — Provides a common structure for collecting violations.

## 5. Scheduling algorithm

### 5.1 Course ordering

The course ordering function sorts courses using these keys:

1. Higher enrolment count first.
2. Higher credit value first when enrolment counts are equal.
3. Course code in ascending alphabetical order as the deterministic tie-breaker.

In Python terms, the ordering key is equivalent to:

```python
(-enrolment_count, -credits, course_code)
```

The enrolment count used by the loader is recalculated from the enrolment records, rather than relying only on a declared count in the course file.

### 5.2 Earliest-feasible-session placement

Available exam-window rows are sorted by date, with FN before AN on the same date. For each course, the scheduler tests candidate sessions in that order. A candidate must pass the student constraint checks and the session's aggregate hall-capacity and hall-packing checks.

If the only remaining issue is the core-course gap preference, the scheduler can retain an otherwise feasible candidate as a soft-gap fallback. That assignment carries a soft-violation message for reporting/inspection. If no feasible or permitted fallback session exists, the course is not silently assigned; a hard scheduling violation is recorded.

### 5.3 Backlog course window

Courses whose `exam_type` is `BACKLOG` are considered only in the final three calendar dates of the exam window. AN is permitted; FN is permitted by the scheduler when the backlog course enrolment is greater than 50.

### 5.4 Capacity checks

For each candidate session, the scheduler sums the capacities of halls available for that date/session and applies the 90% limit. It also invokes hall-packing compatibility checks, so a course is not accepted merely because the aggregate seat total fits if the courses cannot be packed into the available halls under the hall rules.

## 6. Business-rule mapping

The following table maps the PS-067 rule topics to the relevant implementation areas. It is a navigation guide; final compliance should be established by testing each rule and edge case against the official expected outputs.

| Rule | Requirement area | Main implementation |
|---|---|---|
| BR-01 | Student session clashes, daily limit and backlog-consent exception | `engine/constraint_checker.py` |
| BR-02 | Programme-semester gap between core courses | `engine/constraint_checker.py`, `engine/scheduler.py` |
| BR-03 | Course ordering and earliest-feasible placement | `engine/ordering_heuristic.py`, `engine/scheduler.py` |
| BR-04 | 90% aggregate session capacity and duration compatibility | `engine/scheduler.py`, `engine/hall_allocator.py` |
| BR-05 | Hall filling, course mixing and small-course handling | `engine/hall_allocator.py` |
| BR-06 | Seating order, alternate columns and special-needs seating | `engine/seating_engine.py`, `engine/hall_allocator.py` |
| BR-07 | Invigilator eligibility and workload restrictions | `engine/invigilator_allocator.py` |
| BR-08 | Chief invigilator assignment order and unstaffed reporting | `engine/invigilator_allocator.py` |
| BR-09 | Course postponement | `engine/change_manager.py` |
| BR-10 | Hall unavailability and reassignment | `engine/change_manager.py`, `engine/hall_allocator.py` |
| BR-11 | Late registration and clash handling | `engine/change_manager.py` |
| BR-12 | Backlog examination scheduling window | `engine/scheduler.py`, `engine/change_manager.py` |

### Hard and soft constraints

A **hard constraint** is a condition the scheduler or allocator must not accept as a normal valid placement, such as a same-session student clash, an unavailable hall, an incompatible exam duration or a workload limit. A **soft constraint** is a preference that may be relaxed only through the specified fallback and must remain visible as a recorded violation. In this project, the core-course gap check has an explicit soft-gap fallback in the scheduling flow.

## 7. Hall allocation and seating

### 7.1 Hall packing

The hall allocator uses hall capacity and dimensions, course enrolment, department, exam duration and special-needs information to decide whether courses can share a hall. A hall can contain at most two courses. Courses sharing a hall must be from different departments and must have compatible exam durations. The allocator sorts halls by descending capacity for its largest-first packing strategy.

A course with fewer than 10 students is not accepted as the sole course in a hall; the allocator attempts to pair it with a compatible course from another department. If a compatible pairing or placement cannot be found, the course remains unplaced for that allocation pass rather than being silently dropped.

### 7.2 Seating layout

The seating engine creates one record per student/hall allocation. Within each course group, students are ordered by register number. For a two-course hall, the first course is assigned odd-numbered columns and the second course even-numbered columns. This interleaves the two courses so students from the same course are not placed in adjacent columns. For a single-course hall, the implementation uses alternate columns for that course.

Seat coordinates are row and column values. The physical seat number is calculated row-major:

```text
seat_number = (row - 1) * total_columns + column
```

Special-needs students are prioritized for row 1 in ground-floor halls. The seating output records a status if a student cannot be placed in the required position or if a capacity limit is exceeded; such records should be reviewed rather than treated as assigned seats.

### 7.3 Extended hall end time

The hall allocator checks the special-needs status of students assigned to a hall. Where the exam-window data supplies an end time and the hall contains special-needs students, it calculates a 20-minute extended end time and stores it in the hall assignment. The value is exported in `hall_allocation.csv` as `extended_end`.

## 8. Invigilator allocation

The invigilator allocator processes affected date/session groups and maintains workload counters for:

- assignments in an ISO calendar week;
- assignments on a particular date;
- assignments in a particular date/session; and
- total assignments used for tie-breaking.

For each building/session, it first identifies a chief-eligible invigilator. Candidates are filtered by department conflict, unavailable date, maximum two sessions per day, duplicate duty in the same session and individual weekly maximum. Candidates are ordered by fewest assignments so far, then department, then invigilator ID.

After chief reservations, ordinary hall staffing is allocated. The required number is `max(1, ceil(number_of_students / 30))`. Ordinary invigilators are filtered by the hall's course departments and the same availability/workload conditions. If staffing cannot be completed, the allocator records a hard violation rather than inventing an assignment.

## 9. Change-command processing

The command processor reads `change_commands.csv`, sorts rows by the numeric `sequence` field and executes supported commands in order.

Supported command names:

- `POSTPONE`
- `HALL_UNAVAILABLE`
- `ADD_LATE_REGISTRANT`

### 9.1 Postpone a course

`POSTPONE` identifies a course and searches later available sessions. The change manager checks student constraints, backlog restrictions, aggregate capacity and hall-packing feasibility. If a new slot is selected, the course assignment is updated and the old and new date/session pairs are marked as affected. Hall allocations and invigilation rows are rebuilt for those affected sessions.

### 9.2 Mark a hall unavailable

`HALL_UNAVAILABLE` marks a hall unavailable for a date and either one session or all available sessions on that date. The change manager attempts to reallocate the affected session using the remaining available halls and records the outcome.

### 9.3 Add a late registrant

`ADD_LATE_REGISTRANT` identifies a student from the initial student master or the optional late-student file, then asks the change manager to add that student to the requested course. The change manager returns a processed or rejected status, including rejection when the course/student is unknown or a clash prevents registration.

### 9.4 Incremental rebuild concept

The incremental scheduler identifies the old and new session keys for a changed course. The change manager retains hall and roster rows outside the affected session set and regenerates the affected hall allocations and invigilator roster rows. This limits the scope of recalculation compared with rebuilding every session after every command.

## 10. Input data files

All input files are CSV. Dates use ISO format `YYYY-MM-DD`; sessions use `FN` and `AN`; Boolean-style flags use `YES`/`NO` in the supplied dataset.

| File | Purpose | Important fields / notes |
|---|---|---|
| `courses.csv` | Course catalogue | `course_code`, `department`, `semester`, `credits`, `exam_duration_hours`, `exam_type` |
| `students.csv` | Student master | `student_id`, `register_number`, `name`, `programme`, `department`, `semester`, `special_needs`, `backlog_consent` |
| `enrolments.csv` | Course/student relationship | `course_code`, `student_id`, enrolment type |
| `halls.csv` | Examination hall inventory | `hall_id`, `capacity`, `rows`, `columns`, `building`, `floor` |
| `invigilators.csv` | Staff availability and limits | `invigilator_id`, `department`, `max_sessions_per_week`, `unavailable_dates`, `is_chief_eligible` |
| `exam_window.csv` | Candidate examination sessions | `date`, `session`, availability and session time fields |
| `holidays.csv` | Full-day holiday calendar | Holiday dates in the exam window |
| `late_students.csv` | Student records available for late registration | Student identifiers and student attributes |
| `late_enrolments.csv` | Late enrolment fixture | Late student/course relationships supplied with the dataset |
| `change_commands.csv` | Ordered change requests | `sequence`, `command`, `target`, `parameter`, `description` |

`DataLoader` requires the core course, student, enrolment, hall, invigilator, exam-window and holiday files. The late-student, late-enrolment and change-command files are optional at load time; the command file is processed when it exists or when a path is supplied.

## 11. Generated output files

The default output directory is `output/`.

| Output | Format | Contents |
|---|---|---|
| `timetable.csv` | CSV | Course-wise date, session and scheduling details |
| `timetable.txt` | Text | Human-readable examination timetable |
| `hall_allocation.csv` | CSV | Hall, building, capacity, courses, student count, duration and extended end time |
| `seating_plan.csv` | CSV | Student-level hall, course, row, column, seat number and seating status |
| `seating_map.txt` | Text | Hall-wise visual/text seat map |
| `invigilation_roster.csv` | CSV | Invigilator, hall, date, session, role and status |
| `invigilation_roster.txt` | Text | Human-readable invigilation duties |
| `violations.csv` | CSV | Rule ID, severity, entity and violation message |
| `violations.txt` | Text | Violation totals grouped by severity and details |
| `command_results.csv` | CSV | Status and message for each processed change command |

A report with only its header means no violations were recorded by the checks that ran. It should not be interpreted as proof that every hidden test or every business-rule edge case has passed.

## 12. Installation and execution

### Requirements

- Python 3.10 or later.
- No third-party Python packages are required by the current implementation; it uses Python standard-library modules.
- Windows PowerShell, Command Prompt, macOS Terminal or Linux shell.

### Clone the repository

Replace the placeholder with the HTTPS clone address of your GitHub repository:

```bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd T038-PS067
```

### Run with default folders

From the project root:

```bash
python main.py
```

On Windows, if `python` is not mapped to Python 3, use:

```powershell
py main.py
```

### Use custom input/output/command paths

```bash
python main.py --data data --output output --commands data/change_commands.csv
```

Arguments:

- `--data`: directory containing input CSV files (default: `data`).
- `--output`: directory where reports are written (default: `output`).
- `--commands`: change-command CSV path (default: `<data>/change_commands.csv`).

The process prints loaded record counts, number of courses scheduled, number of change commands processed and the report destination. It returns a non-zero exit code when validation or handled input loading/execution errors prevent a normal run.

## 13. Command-file format

The command file uses these columns:

```csv
sequence,command,target,parameter,description
```

Examples:

```csv
1,POSTPONE,CSE101,2026-12-01|FN,Move course to a later slot
2,HALL_UNAVAILABLE,H03,2026-12-02|ALL,Close hall for all sessions that day
3,ADD_LATE_REGISTRANT,LATE001,CSE101,Add student to course
```

| Command | `target` | `parameter` |
|---|---|---|
| `POSTPONE` | Course code | Optional target date and session separated by `|`, e.g. `2026-12-05|AN` |
| `HALL_UNAVAILABLE` | Hall ID | Date and session separated by `|`; use `ALL` for all available sessions on that date |
| `ADD_LATE_REGISTRANT` | Student ID | Course code |

Commands are processed in ascending `sequence` order. Unsupported commands and invalid/unknown targets produce rejected command results rather than being treated as successful operations.

## 14. Validation and error handling

Before scheduling, the input validator checks duplicate course, student, hall and invigilator identifiers; enrolment references to known courses and students; course exam duration values; positive hall capacities; valid ISO dates; and valid FN/AN session names.

During execution, scheduling and allocation components collect violations such as courses that cannot be placed, halls that cannot be staffed and command operations that cannot be completed. The violation report includes severity, rule identifier, affected entity and explanatory message.

Always inspect both `command_results.csv` and `violations.csv` after a run. A successful process exit means the application completed its workflow; it does not automatically mean every requested operation was accepted or every business rule was satisfied.

## 15. Project directory structure

```text
T038-PS067/
│
├── commands/
│   ├── __init__.py
│   ├── command_processor.py
│   └── README.txt
│
├── data/
│   ├── courses.csv
│   ├── students.csv
│   ├── enrolments.csv
│   ├── halls.csv
│   ├── invigilators.csv
│   ├── exam_window.csv
│   ├── holidays.csv
│   ├── late_students.csv
│   ├── late_enrolments.csv
│   ├── change_commands.csv
│   └── README.txt
│
├── engine/
│   ├── __init__.py
│   ├── change_manager.py
│   ├── constraint_checker.py
│   ├── data_loader.py
│   ├── hall_allocator.py
│   ├── incremental_scheduler.py
│   ├── invigilator_allocator.py
│   ├── models.py
│   ├── ordering_heuristic.py
│   ├── scheduler.py
│   ├── seating_engine.py
│   ├── validator.py
│   └── violation_manager.py
│
├── output/                 # Generated reports
├── reports/
│   ├── __init__.py
│   ├── base_report.py
│   ├── hall_report.py
│   ├── invigilation_report.py
│   ├── timetable_report.py
│   └── violation_report.py
│
├── main.py
├── README.md
└── .gitignore
```

Generated output files may be present in the repository after a run; they are regenerated when the application executes.

## 16. Implementation notes and limitations

- This is a backend command-line project. It does not provide a web or desktop user interface.
- The current loader reads CSV files into memory and builds indexes; it does not use a relational database.
- `late_enrolments.csv` is loaded as an optional dataset. The command processor's supported late-registration operation is driven by `ADD_LATE_REGISTRANT` commands and the student/course values in those commands.
- The implementation records explicit statuses for seating records that cannot be assigned a valid seat. Check `seating_plan.csv` for statuses other than `ASSIGNED`.
- Chief and ordinary invigilator shortages are reported as violations. The allocator must not bypass department, unavailable-date or workload restrictions to suppress a warning.
- The exact hidden evaluation dataset and expected-output files are not included in this repository. Final compliance should be established by comparing generated outputs with the official visible and hidden evaluation cases.
- Optional stretch goals in the problem statement (global minimization of sessions used and an invigilator-swap command) are not represented as supported commands in the current command processor.

## 17. Evaluation dataset

The PS-067 specification describes a sample evaluation scale of 120 courses, 2,500 students, 18 halls, 90 invigilators, a 12-day examination window, two holidays and eight change commands. The included `data/README.txt` documents the supplied local dataset, its dates, conventions and fixture files. The runtime counts printed by `main.py` are the authoritative counts for the particular dataset being executed.

---

## Project summary

PS-067 brings together constraint-based timetable generation, hall packing, student seating, invigilator workload allocation, command-driven schedule changes and report generation in a modular Python application. Its purpose is to provide a reproducible backend workflow for university examination planning and to make scheduling decisions and detected violations inspectable through structured output files...
