PS-067 SAMPLE DATASET
=====================

Dataset scale
- 120 courses
- 2,500 initial students
- 5 separate late-registrant records
- Enrolment rows in enrolments.csv (regular and backlog)
- 18 halls
- 90 invigilators
- 12 calendar-day exam window (2026-12-01 through 2026-12-12)
- 2 full holidays (2026-12-04 and 2026-12-08)
- Final-day AN session closed; FN remains available
- 8 change commands

Files
- courses.csv: course metadata and declared enrolment_count
- students.csv: initial student master
- enrolments.csv: many-to-many course/student enrolment records
- halls.csv: hall capacity, dimensions, building and floor
- invigilators.csv: staffing constraints and unavailable dates
- exam_window.csv: available FN/AN sessions
- holidays.csv: full-day holidays
- late_students.csv: students introduced after initial timetable is fixed
- late_enrolments.csv: courses requested for late registration
- change_commands.csv: ordered change-command fixture

Important conventions
- Course exam_type is REGULAR or BACKLOG.
- Enrolment type is REGULAR or BACKLOG.
- Session names are FN and AN.
- Dates use ISO format YYYY-MM-DD.
- Hall floor is GROUND, FIRST or SECOND.
- special_needs and backlog_consent use YES/NO.
- Rows and columns are dimensions; capacity is the authoritative seat limit.
- Course codes are deterministic. Dataset generation uses a fixed seed.

Command-file note
The command file is a test fixture. The final engine should validate each command against its current state and report rejected commands without corrupting the schedule. Command syntax can be mapped directly to the parser implemented in the project. The deliberately unknown AIDS? course in sequence 7 tests invalid-course handling.
