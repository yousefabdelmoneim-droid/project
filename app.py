import os
from datetime import date, datetime, timedelta

from flask import Flask, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from models import Lesson, Student, db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_week_bounds():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def get_all_students():
    return Student.query.order_by(func.lower(Student.name)).all()


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    students = get_all_students()
    today = date.today()
    now_time = datetime.now().strftime("%H:%M")
    week_start, week_end = get_week_bounds()

    # Recent lessons (this week) for the history preview
    recent_lessons = (
        Lesson.query
        .join(Student)
        .filter(Lesson.date >= week_start)
        .order_by(Lesson.date.desc(), Lesson.time.desc())
        .all()
    )

    return render_template(
        "index.html",
        students=students,
        today=today,
        now_time=now_time,
        recent_lessons=recent_lessons,
        view="dashboard",
    )


# ─── Students ─────────────────────────────────────────────────────────────────

@app.route("/students/add", methods=["POST"])
def add_student():
    name = request.form.get("name", "").strip()
    try:
        weekly_plan = int(request.form.get("weekly_plan", 1))
    except ValueError:
        weekly_plan = 1

    if not name:
        flash("Student name cannot be empty.", "error")
        return redirect(url_for("index"))

    if weekly_plan not in (1, 2):
        flash("Weekly plan must be 1 or 2.", "error")
        return redirect(url_for("index"))

    existing = Student.query.filter(func.lower(Student.name) == func.lower(name)).first()
    if existing:
        flash(f'A student named "{existing.name}" already exists.', "error")
        return redirect(url_for("index"))

    student = Student(name=name, weekly_plan=weekly_plan, last_reset_date=date.today())
    db.session.add(student)
    db.session.commit()
    flash(f'Student "{name}" added successfully.', "success")
    return redirect(url_for("index"))


@app.route("/students/<int:student_id>/delete", methods=["POST"])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    name = student.name
    db.session.delete(student)
    db.session.commit()
    flash(f'Student "{name}" and all their lessons have been removed.', "success")
    return redirect(url_for("index"))


@app.route("/students/<int:student_id>/reset", methods=["POST"])
def reset_counter(student_id):
    student = Student.query.get_or_404(student_id)
    student.last_reset_date = date.today()
    db.session.commit()
    flash(f'Counter reset for "{student.name}".', "success")
    return redirect(url_for("index"))


# ─── Lessons ──────────────────────────────────────────────────────────────────

@app.route("/lessons/add", methods=["POST"])
def add_lesson():
    try:
        student_id = int(request.form.get("student_id", 0))
    except ValueError:
        flash("Invalid student.", "error")
        return redirect(url_for("index"))

    date_str = request.form.get("date", "").strip()
    time_str = request.form.get("time", "").strip()

    student = Student.query.get_or_404(student_id)

    try:
        lesson_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format.", "error")
        return redirect(url_for("lessons_view"))

    if not time_str or len(time_str) != 5:
        flash("Invalid time format. Use HH:MM.", "error")
        return redirect(url_for("lessons_view"))

    lesson = Lesson(student_id=student_id, date=lesson_date, time=time_str)
    db.session.add(lesson)
    db.session.commit()
    flash(f'Lesson logged for "{student.name}" on {lesson_date.strftime("%d %b %Y")} at {time_str}.', "success")
    return redirect(url_for("lessons_view"))


@app.route("/lessons/quick-add/<int:student_id>", methods=["POST"])
def quick_add_lesson(student_id):
    student = Student.query.get_or_404(student_id)
    now = datetime.now()
    lesson = Lesson(
        student_id=student_id,
        date=now.date(),
        time=now.strftime("%H:%M"),
    )
    db.session.add(lesson)
    db.session.commit()
    flash(f'Quick lesson logged for "{student.name}" at {lesson.time}.', "success")
    return redirect(url_for("index"))


@app.route("/lessons/<int:lesson_id>/delete", methods=["POST"])
def delete_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    db.session.delete(lesson)
    db.session.commit()
    flash("Lesson removed.", "success")
    return redirect(request.referrer or url_for("lessons_view"))


# ─── Lessons View ─────────────────────────────────────────────────────────────

@app.route("/lessons")
def lessons_view():
    students = get_all_students()
    today = date.today()
    now_time = datetime.now().strftime("%H:%M")
    week_start, _ = get_week_bounds()

    filter_mode = request.args.get("filter", "all")
    student_filter = request.args.get("student", "all")

    query = Lesson.query.join(Student)

    if filter_mode == "week":
        query = query.filter(Lesson.date >= week_start, Lesson.date <= today)

    if student_filter != "all":
        try:
            sid = int(student_filter)
            query = query.filter(Lesson.student_id == sid)
        except ValueError:
            pass

    lessons = query.order_by(Lesson.date.desc(), Lesson.time.desc()).all()

    return render_template(
        "index.html",
        students=students,
        today=today,
        now_time=now_time,
        lessons=lessons,
        filter_mode=filter_mode,
        student_filter=student_filter,
        view="lessons",
    )


# ─── Upcoming ─────────────────────────────────────────────────────────────────

@app.route("/upcoming")
def upcoming_view():
    students = get_all_students()
    today = date.today()
    now_time = datetime.now().strftime("%H:%M")

    upcoming = (
        Lesson.query
        .join(Student)
        .filter(Lesson.date >= today)
        .order_by(Lesson.date.asc(), Lesson.time.asc())
        .all()
    )

    return render_template(
        "index.html",
        students=students,
        today=today,
        now_time=now_time,
        upcoming=upcoming,
        view="upcoming",
    )


if __name__ == "__main__":
    app.run(debug=True)
