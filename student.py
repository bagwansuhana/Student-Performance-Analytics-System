from dataclasses import dataclass


@dataclass
class Student:
    """Simple domain model for student identity; persistence is handled by DatabaseManager."""
    student_id: str
    name: str
    email: str | None
    department: str
    enrollment_year: int

    def validate(self):
        if not self.student_id.strip():
            raise ValueError("Student ID is required.")
        if not self.name.strip():
            raise ValueError("Student name is required.")
        if not self.department.strip():
            raise ValueError("Department is required.")
        if not 1900 <= int(self.enrollment_year) <= 2200:
            raise ValueError("Enrollment year is outside the accepted range.")
        return True
