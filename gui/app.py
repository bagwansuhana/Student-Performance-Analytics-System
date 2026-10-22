from __future__ import annotations

import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from database.db_manager import DatabaseManager
from analytics.engine import AnalyticsEngine
from reports.report_manager import ReportManager


class StudentPerformanceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Student Performance Analytics System")
        self.geometry("1240x790")
        self.minsize(1050, 650)

        self.db = DatabaseManager()
        self.analytics = AnalyticsEngine(self.db)
        self.reports = ReportManager(self.db, self.analytics)

        self._configure_style()
        self._build_ui()
        self.refresh_all()

    def _configure_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Metric.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        header = ttk.Frame(self, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text="Student Performance Analytics", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Import CSV / Excel", command=self.import_marks).pack(side="right", padx=(8, 0))
        ttk.Button(header, text="Export Marks CSV", command=self.export_csv).pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.dashboard_tab = ttk.Frame(self.notebook, padding=12)
        self.students_tab = ttk.Frame(self.notebook, padding=12)
        self.academic_tab = ttk.Frame(self.notebook, padding=12)
        self.analytics_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.students_tab, text="Students")
        self.notebook.add(self.academic_tab, text="Subjects & Marks")
        self.notebook.add(self.analytics_tab, text="Analytics & Reports")

        self._build_dashboard()
        self._build_students()
        self._build_academic()
        self._build_analytics()

    def _build_dashboard(self):
        ttk.Label(self.dashboard_tab, text="Database overview", style="Title.TLabel").pack(anchor="w", pady=(0, 10))
        metrics = ttk.Frame(self.dashboard_tab)
        metrics.pack(fill="x")
        self.metric_labels = {}
        for key, label in [("students", "Students"), ("subjects", "Subjects"), ("semesters", "Semesters"), ("marks", "Mark records")]:
            card = ttk.LabelFrame(metrics, text=label, padding=18)
            card.pack(side="left", fill="x", expand=True, padx=(0, 8))
            value = ttk.Label(card, text="0", style="Metric.TLabel")
            value.pack()
            self.metric_labels[key] = value
        ttk.Label(self.dashboard_tab, text="Low-performance alerts (failed subject or below 40%)",
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(22, 8))
        self.alert_tree = self._make_tree(self.dashboard_tab,
            ("student_id", "student_name", "subject_name", "academic_year", "semester_number", "marks_obtained", "max_marks", "percentage", "alert_reason"),
            ("Student ID", "Student", "Subject", "Year", "Sem", "Marks", "Max", "%", "Alert"), height=12)
        ttk.Button(self.dashboard_tab, text="Refresh dashboard", command=self.refresh_all).pack(anchor="e", pady=8)

    def _build_students(self):
        left = ttk.LabelFrame(self.students_tab, text="Student details", padding=12)
        left.pack(side="left", fill="y", padx=(0, 12))
        self.student_vars = {key: tk.StringVar() for key in ("student_id", "name", "email", "department", "enrollment_year")}
        fields = [
            ("Student ID", "student_id"), ("Full name", "name"), ("Email (optional)", "email"),
            ("Department", "department"), ("Enrollment year", "enrollment_year"),
        ]
        for label, key in fields:
            ttk.Label(left, text=label).pack(anchor="w", pady=(7, 2))
            ttk.Entry(left, textvariable=self.student_vars[key], width=30).pack(fill="x")
        ttk.Button(left, text="Add student", command=self.add_student).pack(fill="x", pady=(14, 4))
        ttk.Button(left, text="Update selected", command=self.update_student).pack(fill="x", pady=4)
        ttk.Button(left, text="Delete selected", command=self.delete_student).pack(fill="x", pady=4)
        ttk.Button(left, text="Clear form", command=self.clear_student_form).pack(fill="x", pady=4)

        right = ttk.Frame(self.students_tab)
        right.pack(side="left", fill="both", expand=True)
        search_row = ttk.Frame(right)
        search_row.pack(fill="x", pady=(0, 8))
        ttk.Label(search_row, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=8)
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_students())
        self.student_tree = self._make_tree(right,
            ("student_id", "name", "email", "department", "enrollment_year"),
            ("Student ID", "Name", "Email", "Department", "Year"))
        self.student_tree.bind("<<TreeviewSelect>>", self.on_student_select)

    def _build_academic(self):
        controls = ttk.LabelFrame(self.academic_tab, text="Add subject / semester / marks", padding=10)
        controls.pack(fill="x", pady=(0, 10))
        self.subject_name_var = tk.StringVar()
        self.max_marks_var = tk.StringVar(value="100")
        self.pass_marks_var = tk.StringVar(value="35")
        self.sem_num_var = tk.StringVar(value="1")
        self.academic_year_var = tk.StringVar(value="2026-27")
        self.mark_student_var = tk.StringVar()
        self.mark_subject_var = tk.StringVar()
        self.mark_semester_var = tk.StringVar()
        self.mark_value_var = tk.StringVar()
        row1 = ttk.Frame(controls)
        row1.pack(fill="x", pady=3)
        self._field(row1, "Subject", self.subject_name_var, 18)
        self._field(row1, "Max marks", self.max_marks_var, 8)
        self._field(row1, "Pass marks", self.pass_marks_var, 8)
        ttk.Button(row1, text="Add subject", command=self.add_subject).pack(side="left", padx=5)
        self._field(row1, "Semester no.", self.sem_num_var, 8)
        self._field(row1, "Academic year", self.academic_year_var, 10)
        ttk.Button(row1, text="Add semester", command=self.add_semester).pack(side="left", padx=5)

        row2 = ttk.Frame(controls)
        row2.pack(fill="x", pady=3)
        self.student_combo = ttk.Combobox(row2, textvariable=self.mark_student_var, state="readonly", width=18)
        self.student_combo.pack(side="left", padx=4)
        self.subject_combo = ttk.Combobox(row2, textvariable=self.mark_subject_var, state="readonly", width=24)
        self.subject_combo.pack(side="left", padx=4)
        self.semester_combo = ttk.Combobox(row2, textvariable=self.mark_semester_var, state="readonly", width=20)
        self.semester_combo.pack(side="left", padx=4)
        ttk.Label(row2, text="Marks").pack(side="left", padx=(8, 2))
        ttk.Entry(row2, textvariable=self.mark_value_var, width=9).pack(side="left")
        ttk.Button(row2, text="Save marks", command=self.save_marks).pack(side="left", padx=6)
        ttk.Button(row2, text="Delete selected mark", command=self.delete_selected_mark).pack(side="left", padx=6)

        ttk.Label(self.academic_tab, text="Mark records (select a row to delete)", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(4, 6))
        self.marks_tree = self._make_tree(self.academic_tab,
            ("mark_id", "student_id", "student_name", "subject_name", "academic_year", "semester_number", "marks_obtained", "max_marks", "pass_marks", "percentage"),
            ("ID", "Student ID", "Student", "Subject", "Year", "Sem", "Marks", "Max", "Pass", "%"), height=15)

    def _build_analytics(self):
        top = ttk.Frame(self.analytics_tab)
        top.pack(fill="x")
        ttk.Label(top, text="Student ID:").pack(side="left")
        self.analytics_student_var = tk.StringVar()
        self.analytics_student_combo = ttk.Combobox(top, textvariable=self.analytics_student_var, state="readonly", width=22)
        self.analytics_student_combo.pack(side="left", padx=6)
        ttk.Button(top, text="Show summary", command=self.show_summary).pack(side="left", padx=4)
        ttk.Button(top, text="Semester trend chart", command=self.show_trend).pack(side="left", padx=4)
        ttk.Button(top, text="Student PDF report", command=self.export_pdf).pack(side="left", padx=4)
        ttk.Button(top, text="Export CSV", command=self.export_csv).pack(side="left", padx=4)
        self.summary_text = tk.Text(self.analytics_tab, height=7, wrap="word", state="disabled")
        self.summary_text.pack(fill="x", pady=10)
        self.chart_frame = ttk.Frame(self.analytics_tab)
        self.chart_frame.pack(fill="both", expand=True)

    def _field(self, parent, label, variable, width):
        group = ttk.Frame(parent)
        group.pack(side="left", padx=4)
        ttk.Label(group, text=label).pack(anchor="w")
        ttk.Entry(group, textvariable=variable, width=width).pack()

    def _make_tree(self, parent, keys, headings, height=10):
        wrap = ttk.Frame(parent)
        wrap.pack(fill="both", expand=True)
        tree = ttk.Treeview(wrap, columns=keys, show="headings", height=height)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        for key, heading in zip(keys, headings):
            tree.heading(key, text=heading)
            tree.column(key, width=max(85, min(160, len(heading) * 10)), anchor="w")
        return tree

    def _selected_values(self, tree):
        selection = tree.selection()
        if not selection:
            return None
        return tree.item(selection[0], "values")

    def _show_error(self, error):
        messagebox.showerror("Operation failed", str(error), parent=self)

    def _show_info(self, text):
        messagebox.showinfo("Student Performance Analytics", text, parent=self)

    def refresh_all(self):
        """Refresh all visible sections; one failed section should not block the others."""
        errors = []
        for refresh in (self.refresh_students, self.refresh_academic, self.refresh_combos, self.refresh_dashboard):
            try:
                refresh()
            except Exception as error:
                errors.append(f"{refresh.__name__}: {error}")
        if errors:
            messagebox.showerror(
                "Refresh warning",
                "Some sections could not refresh:\n\n" + "\n".join(errors),
                parent=self,
            )

    def refresh_students(self):
        if not hasattr(self, "student_tree"):
            return
        for item in self.student_tree.get_children():
            self.student_tree.delete(item)
        for row in self.db.get_all_students(self.search_var.get() if hasattr(self, "search_var") else ""):
            self.student_tree.insert("", "end", values=tuple(row[k] for k in ("student_id", "name", "email", "department", "enrollment_year")))

    def refresh_academic(self):
        if not hasattr(self, "marks_tree"):
            return
        for item in self.marks_tree.get_children():
            self.marks_tree.delete(item)
        for row in self.db.get_all_marks():
            self.marks_tree.insert("", "end", values=(
                row["mark_id"], row["student_id"], row["student_name"], row["subject_name"],
                row["academic_year"], row["semester_number"], row["marks_obtained"],
                row["max_marks"], row["pass_marks"],
                round(float(row["marks_obtained"]) / float(row["max_marks"]) * 100, 2)
            ))

    def refresh_combos(self):
        students = self.db.get_all_students()
        subjects = self.db.get_all_subjects()
        semesters = self.db.get_all_semesters()
        self.student_lookup = {f"{r['student_id']} | {r['name']}": r["student_id"] for r in students}
        self.subject_lookup = {f"{r['subject_id']} | {r['subject_name']} (max {r['max_marks']})": r["subject_id"] for r in subjects}
        self.semester_lookup = {f"{r['semester_id']} | Sem {r['semester_number']} ({r['academic_year']})": r["semester_id"] for r in semesters}
        self.student_combo["values"] = list(self.student_lookup)
        self.subject_combo["values"] = list(self.subject_lookup)
        self.semester_combo["values"] = list(self.semester_lookup)
        self.analytics_student_combo["values"] = [r["student_id"] for r in students]

    def refresh_dashboard(self):
        stats = self.db.get_dashboard_stats()
        for key, value in stats.items():
            self.metric_labels[key].configure(text=str(value))
        for item in self.alert_tree.get_children():
            self.alert_tree.delete(item)
        for row in self.analytics.low_performance_alerts():
            self.alert_tree.insert("", "end", values=(
                row["student_id"], row["student_name"], row["subject_name"], row["academic_year"],
                row["semester_number"], row["marks_obtained"], row["max_marks"],
                row["percentage"], row["alert_reason"]
            ))

    def clear_student_form(self):
        for var in self.student_vars.values():
            var.set("")
        self.student_tree.selection_remove(self.student_tree.selection())

    def on_student_select(self, _event=None):
        values = self._selected_values(self.student_tree)
        if not values:
            return
        for key, value in zip(("student_id", "name", "email", "department", "enrollment_year"), values):
            self.student_vars[key].set("" if value is None else str(value))

    def add_student(self):
        try:
            self.db.add_student(**{k: v.get() for k, v in self.student_vars.items()})
            self.clear_student_form()
            self.refresh_all()
            self._show_info("Student added successfully.")
        except Exception as error:
            self._show_error(error)

    def update_student(self):
        try:
            if not self.student_vars["student_id"].get().strip():
                raise ValueError("Select a student or enter the student ID.")
            self.db.update_student(**{k: v.get() for k, v in self.student_vars.items()})
            self.refresh_all()
            self._show_info("Student updated successfully.")
        except Exception as error:
            self._show_error(error)

    def delete_student(self):
        try:
            sid = self.student_vars["student_id"].get().strip()
            if not sid:
                raise ValueError("Select a student first.")
            if messagebox.askyesno("Confirm deletion", f"Delete {sid} and all associated marks?", parent=self):
                self.db.delete_student(sid)
                self.clear_student_form()
                self.refresh_all()
                self._show_info("Student and associated marks deleted.")
        except Exception as error:
            self._show_error(error)

    def add_subject(self):
        try:
            subject_id = self.db.add_subject(self.subject_name_var.get(), self.max_marks_var.get(), self.pass_marks_var.get())
            self.subject_name_var.set("")
            self.refresh_all()
            self._show_info(f"Subject added. Subject ID: {subject_id}")
        except Exception as error:
            self._show_error(error)

    def add_semester(self):
        try:
            semester_id = self.db.add_semester(self.sem_num_var.get(), self.academic_year_var.get())
            self.refresh_all()
            self._show_info(f"Semester saved. Semester ID: {semester_id}")
        except Exception as error:
            self._show_error(error)

    def save_marks(self):
        try:
            student_key = self.mark_student_var.get()
            subject_key = self.mark_subject_var.get()
            semester_key = self.mark_semester_var.get()
            if not all((student_key, subject_key, semester_key)):
                raise ValueError("Choose a student, subject and semester.")
            mark_id = self.db.add_marks(
                self.student_lookup[student_key], self.subject_lookup[subject_key],
                self.semester_lookup[semester_key], self.mark_value_var.get()
            )
            self.mark_value_var.set("")
            self.refresh_all()
            self._show_info(f"Marks saved successfully (record ID {mark_id}).")
        except Exception as error:
            self._show_error(error)

    def delete_selected_mark(self):
        try:
            values = self._selected_values(self.marks_tree)
            if not values:
                raise ValueError("Select a mark record first.")
            if messagebox.askyesno("Confirm deletion", f"Delete mark record {values[0]}?", parent=self):
                self.db.delete_marks(values[0])
                self.refresh_all()
        except Exception as error:
            self._show_error(error)

    def show_summary(self):
        try:
            sid = self.analytics_student_var.get().strip()
            if not sid:
                raise ValueError("Choose a student.")
            student, summary, rows = self.analytics.student_result(sid)
            lines = [
                f"Student: {student['name']} ({student['student_id']})",
                f"Department: {student['department']} | Enrollment year: {student['enrollment_year']}",
                f"Subjects recorded: {summary['count']}",
                f"Total: {summary['total']:.2f} / {summary['maximum']:.2f}",
                f"Percentage: {summary['percentage']:.2f}% | Grade: {summary['grade']} | Result: {summary['result']}",
            ]
            if summary["failed_subjects"]:
                lines.append("Below pass mark: " + ", ".join(summary["failed_subjects"]))
            if not rows:
                lines.append("No marks have been recorded for this student yet.")
            self.summary_text.configure(state="normal")
            self.summary_text.delete("1.0", "end")
            self.summary_text.insert("1.0", "\n".join(lines))
            self.summary_text.configure(state="disabled")
        except Exception as error:
            self._show_error(error)

    def show_trend(self):
        try:
            sid = self.analytics_student_var.get().strip()
            if not sid:
                raise ValueError("Choose a student.")
            df = self.analytics.semester_trends(sid)
            if df.empty:
                raise ValueError("No semester marks found for this student.")
            for child in self.chart_frame.winfo_children():
                child.destroy()
            fig = Figure(figsize=(8, 3.5), dpi=100)
            ax = fig.add_subplot(111)
            ax.plot(df["semester_label"], df["percentage"], marker="o")
            ax.set_title("Semester-wise performance trend")
            ax.set_ylabel("Percentage")
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis="x", rotation=20)
            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception as error:
            self._show_error(error)

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            parent=self, title="Export marks to CSV", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        try:
            self.reports.export_csv(path)
            self._show_info(f"CSV exported to:\n{path}")
        except Exception as error:
            self._show_error(error)

    def export_pdf(self):
        sid = self.analytics_student_var.get().strip()
        if not sid:
            self._show_error("Choose a student first.")
            return
        path = filedialog.asksaveasfilename(
            parent=self, title="Save student PDF report", defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return
        try:
            self.reports.student_pdf(sid, path)
            self._show_info(f"PDF report saved to:\n{path}")
        except Exception as error:
            self._show_error(error)

    @staticmethod
    def _normalize_header(value):
        return str(value).strip().lower().replace(" ", "_").replace("-", "_")

    def import_marks(self):
        path = filedialog.askopenfilename(
            parent=self, title="Import marks",
            filetypes=[("CSV and Excel files", "*.csv *.xlsx *.xls"), ("CSV files", "*.csv"), ("Excel files", "*.xlsx *.xls")]
        )
        if not path:
            return
        try:
            if path.lower().endswith(".csv"):
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path)
            if df.empty:
                raise ValueError("The selected file has no data rows.")
            df.columns = [self._normalize_header(c) for c in df.columns]
            required = {"student_id", "subject_name", "semester_number", "academic_year", "marks_obtained"}
            missing = required - set(df.columns)
            if missing:
                raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
            imported, errors = 0, []
            for idx, record in df.iterrows():
                try:
                    sid = str(record["student_id"]).strip()
                    if not sid or sid.lower() == "nan":
                        raise ValueError("student_id is empty")
                    student = self.db.get_student(sid)
                    if student is None:
                        name = str(record.get("student_name", sid)).strip()
                        if name.lower() == "nan" or not name:
                            name = sid
                        department = str(record.get("department", "Not specified")).strip()
                        if department.lower() == "nan" or not department:
                            department = "Not specified"
                        email = record.get("email", "")
                        if pd.isna(email):
                            email = ""
                        year = record.get("enrollment_year", 2026)
                        if pd.isna(year):
                            year = 2026
                        self.db.add_student(sid, name, email, department, int(float(year)))
                    subject_name = str(record["subject_name"]).strip()
                    if not subject_name or subject_name.lower() == "nan":
                        raise ValueError("subject_name is empty")
                    found_subject = next((s for s in self.db.get_all_subjects() if s["subject_name"].casefold() == subject_name.casefold()), None)
                    max_marks = record.get("max_marks", 100)
                    pass_marks = record.get("pass_marks", 35)
                    if pd.isna(max_marks): max_marks = 100
                    if pd.isna(pass_marks): pass_marks = 35
                    if found_subject:
                        subject_id = found_subject["subject_id"]
                        if float(max_marks) != float(found_subject["max_marks"]):
                            raise ValueError(f"Subject exists with max marks {found_subject['max_marks']}")
                    else:
                        subject_id = self.db.add_subject(subject_name, float(max_marks), float(pass_marks))
                    semester_id = self.db.add_semester(int(float(record["semester_number"])), str(record["academic_year"]).strip())
                    self.db.add_marks(sid, subject_id, semester_id, float(record["marks_obtained"]))
                    imported += 1
                except Exception as row_error:
                    errors.append(f"Row {idx + 2}: {row_error}")
            self.refresh_all()
            message = f"Imported/updated {imported} mark row(s)."
            if errors:
                message += "\n\nRows skipped:\n" + "\n".join(errors[:12])
                if len(errors) > 12:
                    message += f"\n...and {len(errors) - 12} more error(s)."
            messagebox.showinfo("Import finished", message, parent=self)
        except Exception as error:
            self._show_error(error)
