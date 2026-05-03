from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime, timedelta

db = SQLAlchemy()


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    weekly_plan = db.Column(db.Integer, nullable=False, default=1)
    last_reset_date = db.Column(db.Date, nullable=False, default=date.today)

    lessons = db.relationship("Lesson", backref="student", lazy=True, cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("ix_students_name_nocase", db.func.lower("name")),
    )

    @property
    def lessons_since_reset(self):
        return Lesson.query.filter(
            Lesson.student_id == self.id,
            Lesson.date >= self.last_reset_date,
        ).count()

    @property
    def lessons_this_week(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        return Lesson.query.filter(
            Lesson.student_id == self.id,
            Lesson.date >= week_start,
            Lesson.date <= today,
        ).count()

    @property
    def weekly_warning(self):
        return self.lessons_this_week < self.weekly_plan

    def __repr__(self):
        return f"<Student {self.name}>"


class Lesson(db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    time = db.Column(db.String(5), nullable=False)

    def __repr__(self):
        return f"<Lesson {self.student_id} {self.date} {self.time}>"
