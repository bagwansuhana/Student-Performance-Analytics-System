# Student Performance Analytics System

A complete, modular Python desktop project for managing students, subjects, semesters, marks, and academic performance. The UI uses Tkinter; SQLite stores records; Pandas/OpenPyXL handle CSV and Excel imports; Matplotlib displays semester trends; ReportLab creates PDF reports.

## Included features

- Dashboard counts and low-performance alerts
- Student registration, editing, deletion, and live search
- Subject setup with maximum and passing marks
- Semester setup by semester number and academic year
- Marks entry, validation, update-on-duplicate, and deletion
- Analytics: totals, percentages, grades, pass/fail, and failed subjects
- Semester-wise performance trend chart
- CSV and Excel (`.xlsx`) marks import
- CSV export and PDF student report
- SQLite schema initialization and foreign-key validation
- Database CRUD/validation test script
- Import template and Windows setup/launch scripts

## Project structure

```text
StudentPerformanceAnalytics_Complete/
├── main.py
├── student.py
├── initialize_database.py
├── test_db.py
├── requirements.txt
├── setup_windows.bat
├── run_app.bat
├── IMPORT_TEMPLATE.csv
├── database/
│   ├── __init__.py
│   └── db_manager.py
├── analytics/
│   ├── __init__.py
│   └── engine.py
├── gui/
│   ├── __init__.py
│   └── app.py
├── reports/
│   ├── __init__.py
│   └── report_manager.py
├── data/       # SQLite database is created here automatically
└── exports/    # Use this for exported reports/files
```

The `.venv` virtual environment is deliberately **not included**. It is created on your own Windows computer so installed packages match your Python installation. All project source files are included.

## Quick start (Windows)

1. Extract this ZIP to a normal folder, for example `C:\Users\YourName\Documents\StudentPerformanceAnalytics_Complete`.
2. Install Python 3.10 or newer. During installation, enable Python PATH support.
3. Double-click `setup_windows.bat` once. It creates `.venv` and installs requirements.
4. Double-click `run_app.bat` to launch the desktop application.

### Start from VS Code instead

Open the extracted project folder in VS Code, then in the terminal run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python initialize_database.py
python main.py
```

If PowerShell blocks activation, you can skip activation and use `.venv\Scripts\python.exe -m pip install -r requirements.txt` followed by `.venv\Scripts\python.exe main.py`.

## Test before using

Run from the project root:

```powershell
python test_db.py
```

Expected message:

```text
All database CRUD and validation tests passed.
```

The test uses a temporary database and does not erase the application's `data/students.db`.

## Importing marks

Use `IMPORT_TEMPLATE.csv` as a starting point. Required headers:

- `student_id`
- `subject_name`
- `semester_number`
- `academic_year`
- `marks_obtained`

Optional headers: `student_name`, `email`, `department`, `enrollment_year`, `max_marks`, `pass_marks`.

The app can create a student, subject, or semester if it does not already exist. Existing marks for the same student, subject, and semester are updated. Review imported rows and errors shown in the import summary.

## Grade rules

- A+: 90% and above
- A: 80–89.99%
- B: 70–79.99%
- C: 60–69.99%
- D: 50–59.99%
- E: 35–49.99%
- F: below 35% or if any recorded subject is below its configured pass mark

Overall percentage = total marks earned / total possible marks × 100. A student can have a high overall percentage and still be marked FAIL if a subject is below its pass mark.


