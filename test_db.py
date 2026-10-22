from pathlib import Path
import tempfile

from database.db_manager import DatabaseManager


def run_tests():
    with tempfile.TemporaryDirectory() as folder:
        db = DatabaseManager(Path(folder) / "test_students.db")

        db.add_student("S1001", "Aarav Sharma", "aarav@example.com", "Computer Engineering", 2026)
        subject_id = db.add_subject("Python", 100, 35)
        semester_id = db.add_semester(1, "2026-27")
        mark_id = db.add_marks("S1001", subject_id, semester_id, 85)

        assert db.get_student("S1001")["name"] == "Aarav Sharma"
        rows = db.get_student_marks("S1001")
        assert len(rows) == 1 and rows[0]["subject_name"] == "Python"
        assert rows[0]["marks_obtained"] == 85

        db.update_student("S1001", "Aarav S. Sharma", "aarav@example.com", "Computer Engineering", 2026)
        assert db.get_student("S1001")["name"] == "Aarav S. Sharma"
        db.update_marks(mark_id, 90)
        assert db.get_student_marks("S1001")[0]["marks_obtained"] == 90

        try:
            db.add_marks("S1001", subject_id, semester_id, 101)
        except ValueError:
            pass
        else:
            raise AssertionError("Marks above maximum should be rejected")

        db.delete_marks(mark_id)
        assert db.get_student_marks("S1001") == []
        db.delete_student("S1001")
        assert db.get_student("S1001") is None

    print("All database CRUD and validation tests passed.")


if __name__ == "__main__":
    run_tests()
