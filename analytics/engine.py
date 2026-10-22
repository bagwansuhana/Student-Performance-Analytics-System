from __future__ import annotations

import pandas as pd


class AnalyticsEngine:
    def __init__(self, db):
        self.db = db

    def student_result(self, student_id, semester_id=None):
        student = self.db.get_student(student_id)
        if student is None:
            raise ValueError("Student not found.")
        summary = self.db.get_student_summary(student_id, semester_id)
        return dict(student), summary, [dict(row) for row in self.db.get_student_marks(student_id, semester_id)]

    def low_performance_alerts(self, threshold=40.0, semester_id=None):
        rows = [dict(r) for r in self.db.get_all_marks(semester_id)]
        alerts = []
        for row in rows:
            pct = float(row["marks_obtained"]) / float(row["max_marks"]) * 100
            if float(row["marks_obtained"]) < float(row["pass_marks"]) or pct < threshold:
                alerts.append({
                    **row,
                    "percentage": round(pct, 2),
                    "alert_reason": "Below pass mark" if float(row["marks_obtained"]) < float(row["pass_marks"]) else f"Below {threshold:g}% threshold",
                })
        return alerts

    def subject_averages(self, semester_id=None):
        rows = [dict(r) for r in self.db.get_all_marks(semester_id)]
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df["percentage"] = df["marks_obtained"] / df["max_marks"] * 100
        return df.groupby("subject_name", as_index=False).agg(
            average_marks=("marks_obtained", "mean"),
            average_percentage=("percentage", "mean"),
            student_count=("student_id", "nunique"),
        ).sort_values("average_percentage", ascending=False)

    def semester_trends(self, student_id):
        rows = [dict(r) for r in self.db.get_student_marks(student_id)]
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        grouped = df.groupby(["academic_year", "semester_number"], as_index=False).agg(
            total_marks=("marks_obtained", "sum"),
            maximum_marks=("max_marks", "sum"),
        )
        grouped["percentage"] = grouped["total_marks"] / grouped["maximum_marks"] * 100
        grouped["semester_label"] = grouped["academic_year"].astype(str) + " - Sem " + grouped["semester_number"].astype(str)
        return grouped.sort_values(["academic_year", "semester_number"])

    def marks_dataframe(self, semester_id=None):
        rows = [dict(r) for r in self.db.get_all_marks(semester_id)]
        df = pd.DataFrame(rows)
        if not df.empty:
            df["percentage"] = df["marks_obtained"] / df["max_marks"] * 100
            df["passed"] = df["marks_obtained"] >= df["pass_marks"]
        return df
