# T038-PS067
# University Exam Timetabling and Hall Allocation Engine

A Python-based examination management engine designed to automate university examination scheduling, student allocation, hall assignment, and invigilation planning.

## Overview

University examination departments face several challenges when organizing examinations, including student timetable clashes, limited examination hall capacity, invigilator availability, and scheduling constraints.

This project aims to simplify these operations through an automated examination timetabling and hall allocation system.

## Key Features

- Automated examination scheduling
- Student examination allocation
- Student clash detection
- Examination hall allocation
- Hall capacity management
- Invigilator allocation
- Late enrollment handling
- Examination schedule validation
- Report generation

*Note: Confirm each feature against the implemented modules before final submission.*

## Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Data Storage | CSV |
| Version Control | Git |
| Repository Hosting | GitHub |

## Project Structure

```text
T038-PS067/
│
├── commands/
│   ├── command_processor.py
│   └── README.txt
│
├── data/
│   ├── courses.csv
│   ├── students.csv
│   ├── enrollments.csv
│   ├── halls.csv
│   ├── invigilators.csv
│   ├── holidays.csv
│   └── exam_window.csv
│
├── engine/
│   ├── change_manager.py
│   ├── constraint_checker.py
│   ├── data_loader.py
│   ├── hall_allocator.py
│   ├── incremental_scheduler.py
│   ├── invigilator_allocator.py
│   ├── scheduler.py
│   ├── seating_engine.py
│   └── validator.py
│
├── output/
│
├── reports/
│
├── main.py
├── README.md
└── .gitignore
```

## Project Objectives

1. Automate university examination scheduling.
2. Minimize student examination clashes.
3. Allocate students to examination halls.
4. Manage invigilator assignments.
5. Handle scheduling constraints.
6. Generate structured examination reports.

## Installation

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

Navigate into the project directory:

```bash
cd T038-PS067
```

Run the application:

```bash
python main.py
```

## Future Improvements

- Web-based examination management dashboard
- Interactive timetable visualization
- Advanced scheduling optimization
- Database integration
- Improved analytics and reporting

## Project Information

**Project ID:** PS-067

**Domain:** Education – University Examinations

**Project Name:** University Exam Timetabling and Hall Allocation Engine

**Repository:** T038-PS067

---

Developed as a software engineering project focused on automating university examination management.
