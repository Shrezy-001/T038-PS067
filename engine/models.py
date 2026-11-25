from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Violation:
    rule_id: str
    severity: str
    entity: str
    message: str

@dataclass
class Assignment:
    course_code: str
    date: str
    session: str
    duration: int
    students: list[str] = field(default_factory=list)
    soft_violations: list[str] = field(default_factory=list)

@dataclass
class HallAssignment:
    date: str
    session: str
    hall_id: str
    courses: list[str]
    students: list[str]
    duration: int
    extended_end: Optional[str] = None
