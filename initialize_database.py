"""Initialize the application's SQLite database without opening the GUI."""
from database.db_manager import DatabaseManager

if __name__ == "__main__":
    db = DatabaseManager()
    print(f"Database initialized successfully at: {db.db_path}")
    print("Tables are ready: students, subjects, semesters, marks.")
