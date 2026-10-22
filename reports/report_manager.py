from pathlib import Path
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


class ReportManager:
    def __init__(self, db, analytics):
        self.db = db
        self.analytics = analytics

    def export_csv(self, path, semester_id=None):
        df = self.analytics.marks_dataframe(semester_id)
        if df.empty:
            raise ValueError("There are no marks to export.")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        return Path(path)

    def student_pdf(self, student_id, path, semester_id=None):
        student, summary, rows = self.analytics.student_result(student_id, semester_id)
        if not rows:
            raise ValueError("No marks found for this student and selection.")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), rightMargin=24, leftMargin=24)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("Student Performance Report", styles["Title"]),
            Spacer(1, 10),
            Paragraph(f"<b>Student ID:</b> {student['student_id']} &nbsp;&nbsp; <b>Name:</b> {student['name']}", styles["Normal"]),
            Paragraph(f"<b>Department:</b> {student['department']} &nbsp;&nbsp; <b>Enrollment Year:</b> {student['enrollment_year']}", styles["Normal"]),
            Spacer(1, 8),
            Paragraph(
                f"<b>Total:</b> {summary['total']:.2f}/{summary['maximum']:.2f} &nbsp;&nbsp; "
                f"<b>Percentage:</b> {summary['percentage']:.2f}% &nbsp;&nbsp; "
                f"<b>Grade:</b> {summary['grade']} &nbsp;&nbsp; <b>Result:</b> {summary['result']}",
                styles["Normal"]
            ),
            Spacer(1, 12),
        ]
        data = [["Academic Year", "Semester", "Subject", "Marks", "Maximum", "Pass Mark", "Percentage", "Status"]]
        for r in rows:
            data.append([
                str(r["academic_year"]), str(r["semester_number"]), str(r["subject_name"]),
                f"{float(r['marks_obtained']):.2f}", f"{float(r['max_marks']):.2f}",
                f"{float(r['pass_marks']):.2f}", f"{float(r['percentage']):.2f}%",
                "PASS" if float(r["marks_obtained"]) >= float(r["pass_marks"]) else "FAIL",
            ])
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243b53")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
        doc.build(story)
        return Path(path)
