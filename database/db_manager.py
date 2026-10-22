from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "students.db"


class DatabaseManager:
    """SQLite persistence layer. Each operation owns and closes its connection."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.create_tables()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def create_tables(self) -> None:
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
                    email TEXT UNIQUE,
                    department TEXT NOT NULL CHECK(length(trim(department)) > 0),
                    enrollment_year INTEGER NOT NULL CHECK(enrollment_year BETWEEN 1900 AND 2200),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS subjects (
                    subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_name TEXT NOT NULL UNIQUE CHECK(length(trim(subject_name)) > 0),
                    max_marks REAL NOT NULL DEFAULT 100 CHECK(max_marks > 0),
                    pass_marks REAL NOT NULL DEFAULT 35 CHECK(pass_marks >= 0 AND pass_marks <= max_marks)
                );

                CREATE TABLE IF NOT EXISTS semesters (
                    semester_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    semester_number INTEGER NOT NULL CHECK(semester_number > 0),
                    academic_year TEXT NOT NULL CHECK(length(trim(academic_year)) > 0),
                    UNIQUE(semester_number, academic_year)
                );

                CREATE TABLE IF NOT EXISTS marks (
                    mark_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    subject_id INTEGER NOT NULL,
                    semester_id INTEGER NOT NULL,
                    marks_obtained REAL NOT NULL CHECK(marks_obtained >= 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    FOREIGN KEY(subject_id) REFERENCES subjects(subject_id) ON DELETE RESTRICT,
                    FOREIGN KEY(semester_id) REFERENCES semesters(semester_id) ON DELETE RESTRICT,
                    UNIQUE(student_id, subject_id, semester_id)
                );

                CREATE INDEX IF NOT EXISTS idx_marks_student ON marks(student_id);
                CREATE INDEX IF NOT EXISTS idx_marks_semester ON marks(semester_id);
                CREATE INDEX IF NOT EXISTS idx_marks_subject ON marks(subject_id);
            """)
            # Upgrade databases created by earlier versions of this project.
            # CREATE TABLE IF NOT EXISTS does not change an existing table schema.
            self._migrate_legacy_schema(conn)
            # SQLite cannot express a cross-table CHECK for marks <= subjects.max_marks;
            # enforce it in Python for inserts/updates and import.

    @staticmethod
    def _migrate_legacy_schema(conn: sqlite3.Connection) -> None:
        """Safely adapt older table column names without deleting existing records."""
        def columns(table: str) -> set[str]:
            return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}

        # Older versions sometimes used `name` or `subject` instead of subject_name.
        subject_cols = columns("subjects")
        if "subject_name" not in subject_cols:
            for old_name in ("name", "subject"):
                if old_name in subject_cols:
                    conn.execute(f"ALTER TABLE subjects RENAME COLUMN {old_name} TO subject_name")
                    subject_cols.remove(old_name)
                    subject_cols.add("subject_name")
                    break
        if "subject_id" not in subject_cols and "id" in subject_cols:
            conn.execute("ALTER TABLE subjects RENAME COLUMN id TO subject_id")
            subject_cols.remove("id")
            subject_cols.add("subject_id")
        if "max_marks" not in subject_cols:
            conn.execute("ALTER TABLE subjects ADD COLUMN max_marks REAL NOT NULL DEFAULT 100")
        if "pass_marks" not in subject_cols:
            conn.execute("ALTER TABLE subjects ADD COLUMN pass_marks REAL NOT NULL DEFAULT 35")

        # Older versions may have called these columns semester/sem_no and year.
        semester_cols = columns("semesters")
        if "semester_id" not in semester_cols and "id" in semester_cols:
            conn.execute("ALTER TABLE semesters RENAME COLUMN id TO semester_id")
            semester_cols.remove("id")
            semester_cols.add("semester_id")
        if "semester_number" not in semester_cols:
            for old_name in ("semester", "sem_no", "sem_number"):
                if old_name in semester_cols:
                    conn.execute(f"ALTER TABLE semesters RENAME COLUMN {old_name} TO semester_number")
                    semester_cols.remove(old_name)
                    semester_cols.add("semester_number")
                    break
        if "academic_year" not in semester_cols:
            for old_name in ("year", "session", "academic_session"):
                if old_name in semester_cols:
                    conn.execute(f"ALTER TABLE semesters RENAME COLUMN {old_name} TO academic_year")
                    semester_cols.remove(old_name)
                    semester_cols.add("academic_year")
                    break

        # Some old marks tables lack timestamps; add them only when absent.
        marks_cols = columns("marks")
        if "created_at" not in marks_cols:
            conn.execute("ALTER TABLE marks ADD COLUMN created_at TEXT")
            conn.execute("UPDATE marks SET created_at=CURRENT_TIMESTAMP WHERE created_at IS NULL")
        if "updated_at" not in marks_cols:
            conn.execute("ALTER TABLE marks ADD COLUMN updated_at TEXT")
            conn.execute("UPDATE marks SET updated_at=CURRENT_TIMESTAMP WHERE updated_at IS NULL")

    @staticmethod
    def _clean_required(value: Any, label: str) -> str:
        result = str(value).strip() if value is not None else ""
        if not result:
            raise ValueError(f"{label} is required.")
        return result

    @staticmethod
    def _optional_email(email: str | None) -> str | None:
        value = (email or "").strip()
        if not value:
            return None
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return value

    def add_student(self, student_id, name, email, department, enrollment_year):
        sid = self._clean_required(student_id, "Student ID")
        name = self._clean_required(name, "Name")
        department = self._clean_required(department, "Department")
        email = self._optional_email(email)
        year = int(enrollment_year)
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO students(student_id,name,email,department,enrollment_year) VALUES(?,?,?,?,?)",
                (sid, name, email, department, year),
            )
        return sid

    def update_student(self, student_id, name, email, department, enrollment_year):
        sid = self._clean_required(student_id, "Student ID")
        name = self._clean_required(name, "Name")
        department = self._clean_required(department, "Department")
        email = self._optional_email(email)
        with self.connect() as conn:
            cur = conn.execute(
                """UPDATE students SET name=?,email=?,department=?,enrollment_year=?
                   WHERE student_id=?""",
                (name, email, department, int(enrollment_year), sid),
            )
            if cur.rowcount == 0:
                raise ValueError(f"Student ID {sid} was not found.")
        return True

    def delete_student(self, student_id):
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM students WHERE student_id=?", (student_id,))
            if cur.rowcount == 0:
                raise ValueError(f"Student ID {student_id} was not found.")

    def get_student(self, student_id):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM students WHERE student_id=?", (student_id,)).fetchone()

    def get_all_students(self, search=""):
        term = f"%{search.strip()}%"
        with self.connect() as conn:
            return conn.execute(
                """SELECT * FROM students
                   WHERE student_id LIKE ? OR name LIKE ? OR department LIKE ?
                   ORDER BY name COLLATE NOCASE""",
                (term, term, term),
            ).fetchall()

    def add_subject(self, subject_name, max_marks=100, pass_marks=35):
        name = self._clean_required(subject_name, "Subject name")
        maximum, passing = float(max_marks), float(pass_marks)
        if maximum <= 0:
            raise ValueError("Maximum marks must be greater than zero.")
        if passing < 0 or passing > maximum:
            raise ValueError("Pass marks must be between zero and maximum marks.")
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT subject_id,max_marks,pass_marks FROM subjects WHERE lower(subject_name)=lower(?)",
                (name,),
            ).fetchone()
            if existing:
                if float(existing["max_marks"]) != maximum or float(existing["pass_marks"]) != passing:
                    raise ValueError(
                        f"Subject '{name}' already exists with max marks {existing['max_marks']} "
                        f"and pass marks {existing['pass_marks']}."
                    )
                return existing["subject_id"]
            conn.execute(
                "INSERT INTO subjects(subject_name,max_marks,pass_marks) VALUES(?,?,?)",
                (name, maximum, passing),
            )
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_all_subjects(self):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM subjects ORDER BY subject_name").fetchall()

    def get_subject(self, subject_id):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM subjects WHERE subject_id=?", (subject_id,)).fetchone()

    def add_semester(self, semester_number, academic_year):
        number = int(semester_number)
        year = self._clean_required(academic_year, "Academic year")
        if number < 1:
            raise ValueError("Semester number must be positive.")
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT semester_id FROM semesters WHERE semester_number=? AND academic_year=?",
                (number, year),
            ).fetchone()
            if existing:
                return existing["semester_id"]
            conn.execute(
                "INSERT INTO semesters(semester_number,academic_year) VALUES(?,?)",
                (number, year),
            )
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_all_semesters(self):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM semesters ORDER BY academic_year DESC, semester_number"
            ).fetchall()

    def get_semester(self, semester_id):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM semesters WHERE semester_id=?", (semester_id,)).fetchone()

    def add_marks(self, student_id, subject_id, semester_id, marks_obtained):
        marks = float(marks_obtained)
        subject = self.get_subject(subject_id)
        if subject is None:
            raise ValueError("Subject does not exist.")
        if self.get_student(student_id) is None:
            raise ValueError("Student does not exist.")
        if self.get_semester(semester_id) is None:
            raise ValueError("Semester does not exist.")
        if marks < 0 or marks > subject["max_marks"]:
            raise ValueError(f"Marks must be between 0 and {subject['max_marks']}.")
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO marks(student_id,subject_id,semester_id,marks_obtained)
                   VALUES(?,?,?,?)
                   ON CONFLICT(student_id,subject_id,semester_id)
                   DO UPDATE SET marks_obtained=excluded.marks_obtained,
                                 updated_at=CURRENT_TIMESTAMP""",
                (student_id, int(subject_id), int(semester_id), marks),
            )
            row = conn.execute(
                "SELECT mark_id FROM marks WHERE student_id=? AND subject_id=? AND semester_id=?",
                (student_id, int(subject_id), int(semester_id)),
            ).fetchone()
            return row["mark_id"]

    def update_marks(self, mark_id, marks_obtained):
        marks = float(marks_obtained)
        with self.connect() as conn:
            row = conn.execute(
                """SELECT m.mark_id,s.max_marks FROM marks m
                   JOIN subjects s ON s.subject_id=m.subject_id WHERE m.mark_id=?""",
                (int(mark_id),),
            ).fetchone()
            if row is None:
                raise ValueError("Mark record was not found.")
            if marks < 0 or marks > row["max_marks"]:
                raise ValueError(f"Marks must be between 0 and {row['max_marks']}.")
            conn.execute(
                "UPDATE marks SET marks_obtained=?,updated_at=CURRENT_TIMESTAMP WHERE mark_id=?",
                (marks, int(mark_id)),
            )

    def delete_marks(self, mark_id):
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM marks WHERE mark_id=?", (int(mark_id),))
            if cur.rowcount == 0:
                raise ValueError("Mark record was not found.")

    def get_student_marks(self, student_id, semester_id=None):
        query = """SELECT m.mark_id,m.student_id,st.name AS student_name,
                          m.subject_id,s.subject_name,s.max_marks,s.pass_marks,
                          m.semester_id,sem.semester_number,sem.academic_year,
                          m.marks_obtained,
                          ROUND(100.0*m.marks_obtained/s.max_marks,2) AS percentage,
                          CASE WHEN m.marks_obtained < s.pass_marks THEN 0 ELSE 1 END AS passed
                   FROM marks m
                   JOIN students st ON st.student_id=m.student_id
                   JOIN subjects s ON s.subject_id=m.subject_id
                   JOIN semesters sem ON sem.semester_id=m.semester_id
                   WHERE m.student_id=?"""
        params = [student_id]
        if semester_id is not None:
            query += " AND m.semester_id=?"
            params.append(int(semester_id))
        query += " ORDER BY sem.academic_year,sem.semester_number,s.subject_name"
        with self.connect() as conn:
            return conn.execute(query, params).fetchall()

    def get_all_marks(self, semester_id=None):
        query = """SELECT m.mark_id,m.student_id,st.name AS student_name,
                          s.subject_name,s.max_marks,s.pass_marks,
                          sem.semester_number,sem.academic_year,m.marks_obtained
                   FROM marks m JOIN students st ON st.student_id=m.student_id
                   JOIN subjects s ON s.subject_id=m.subject_id
                   JOIN semesters sem ON sem.semester_id=m.semester_id"""
        params = []
        if semester_id is not None:
            query += " WHERE m.semester_id=?"
            params.append(int(semester_id))
        query += " ORDER BY st.name,s.subject_name"
        with self.connect() as conn:
            return conn.execute(query, params).fetchall()

    def get_student_summary(self, student_id, semester_id=None):
        rows = self.get_student_marks(student_id, semester_id)
        if not rows:
            return {"count": 0, "total": 0.0, "maximum": 0.0, "percentage": 0.0,
                    "grade": "N/A", "result": "NO DATA", "failed_subjects": []}
        total = sum(float(r["marks_obtained"]) for r in rows)
        maximum = sum(float(r["max_marks"]) for r in rows)
        percentage = (total / maximum * 100) if maximum else 0.0
        failed = [r["subject_name"] for r in rows if float(r["marks_obtained"]) < float(r["pass_marks"])]
        if failed:
            grade, result = "F", "FAIL"
        elif percentage >= 90: grade = "A+"
        elif percentage >= 80: grade = "A"
        elif percentage >= 70: grade = "B"
        elif percentage >= 60: grade = "C"
        elif percentage >= 50: grade = "D"
        elif percentage >= 35: grade = "E"
        else: grade = "F"
        return {"count": len(rows), "total": total, "maximum": maximum,
                "percentage": percentage, "grade": grade,
                "result": "PASS" if grade != "F" else "FAIL",
                "failed_subjects": failed}

    def get_dashboard_stats(self):
        with self.connect() as conn:
            students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            subjects = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
            semesters = conn.execute("SELECT COUNT(*) FROM semesters").fetchone()[0]
            marks = conn.execute("SELECT COUNT(*) FROM marks").fetchone()[0]
        return {"students": students, "subjects": subjects, "semesters": semesters, "marks": marks}
