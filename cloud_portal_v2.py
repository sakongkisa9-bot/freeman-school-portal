from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import json
from datetime import datetime
import logging
from functools import wraps

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(PROJECT_DIR, "templates")
app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-2026")

DB_PATH = os.path.join(PROJECT_DIR, "cloud_portal.db")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

EXAM_TITLE_DEFAULT = "TERM 1 EXAM 2026"

GRADE_OPTIONS = [
    "Playgroup",
    "Pre-Primary 1",
    "Pre-Primary 2",
    "Grade 1",
    "Grade 2",
    "Grade 3",
    "Grade 4",
    "Grade 5",
    "Grade 6",
    "Grade 7",
    "Grade 8",
    "Grade 9",
]

GRADE_SUBJECTS = {
    "Playgroup": ["LANG", "MATH", "ENV", "CREAT"],
    "Pre-Primary 1": ["LANG", "MATH", "ENV", "PSYCH", "REL"],
    "Pre-Primary 2": ["LANG", "MATH", "ENV", "PSYCH", "REL"],
    "Grade 1": ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"],
    "Grade 2": ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"],
    "Grade 3": ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"],
    "Grade 4": ["ENG", "KISW", "MATH", "SCIE", "AGRI", "SST", "CRE", "C/A", "PHE"],
    "Grade 5": ["ENG", "KISW", "MATH", "SCIE", "AGRI", "SST", "CRE", "C/A", "PHE"],
    "Grade 6": ["ENG", "KISW", "MATH", "SCIE", "AGRI", "SST", "CRE", "C/A", "PHE"],
    "Grade 7": [
        "MATH",
        "ENG",
        "KISW",
        "INT SCIE",
        "PRE-TECH",
        "SST",
        "CRE",
        "AGRI",
        "C/A",
    ],
    "Grade 8": [
        "MATH",
        "ENG",
        "KISW",
        "INT SCIE",
        "PRE-TECH",
        "SST",
        "CRE",
        "AGRI",
        "C/A",
    ],
    "Grade 9": [
        "MATH",
        "ENG",
        "KISW",
        "INT SCIE",
        "PRE-TECH",
        "SST",
        "CRE",
        "AGRI",
        "C/A",
    ],
}
SYSTEM_ADMIN_KEY = "16592@FREE man"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT NOT NULL,
            school_code TEXT NOT NULL UNIQUE,
            email TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'teacher',
            created_at TEXT NOT NULL,
            UNIQUE(school_id, username),
            FOREIGN KEY(school_id) REFERENCES schools(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            grade TEXT NOT NULL,
            adm_no TEXT NOT NULL,
            student_name TEXT NOT NULL,
            gender TEXT,
            phone TEXT,
            UNIQUE(school_id, grade, adm_no),
            FOREIGN KEY(school_id) REFERENCES schools(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            grade TEXT NOT NULL,
            adm_no TEXT NOT NULL,
            student_name TEXT NOT NULL,
            exam_title TEXT NOT NULL,
            subject_scores_json TEXT NOT NULL,
            total_points TEXT,
            average_level TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(school_id, grade, adm_no, exam_title),
            FOREIGN KEY(school_id) REFERENCES schools(id)
        )
    """)
    conn.commit()
    conn.close()


def authenticate_user(school_code, username, password):
    conn = get_db()
    school = conn.execute(
        "SELECT * FROM schools WHERE school_code = ?", (school_code,)
    ).fetchone()
    if not school:
        conn.close()
        return None, "School code not found."
    teacher = conn.execute(
        "SELECT * FROM teachers WHERE school_id = ? AND username = ?",
        (school["id"], username),
    ).fetchone()
    conn.close()
    if not teacher or not check_password_hash(teacher["password_hash"], password):
        return None, "Invalid username or password."
    return {"school": school, "teacher": teacher}, None


def is_admin():
    return session.get("role") == "admin"


init_db()


@app.route("/")
def home():
    # If they aren't logged in, send them straight to login
    if "school_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Check the Master Key first
        master_key = request.form.get("master_key")
        if master_key != SYSTEM_ADMIN_KEY:
            flash("Unauthorized: Invalid System Admin Key.", "danger")
            return redirect(url_for("register"))

        sn = request.form.get("school_name", "").strip()
        sc = request.form.get("school_code", "").strip().lower()
        se = request.form.get("email", "").strip()
        un = request.form.get("username", "").strip().lower()
        pw = request.form.get("password", "")

        conn = get_db()
        try:
            ph = generate_password_hash(pw)
            now = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT INTO schools (school_name, school_code, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (sn, sc, se, ph, now),
            )
            row = conn.execute(
                "SELECT id FROM schools WHERE school_code = ?", (sc,)
            ).fetchone()
            # This makes the first user an 'admin' (The Principal/Owner)
            conn.execute(
                "INSERT INTO teachers (school_id, username, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (row["id"], un, ph, "admin", now),
            )
            conn.commit()
            flash(f"School {sn} Registered Successfully!", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("School code already exists.", "danger")
        finally:
            conn.close()
    return render_template("cloud_register.html")


@app.route("/delete_school/<school_code>", methods=["POST"])
def delete_school(school_code):
    # Only you should call this via a tool or manual entry
    master_key = request.form.get("master_key")
    if master_key == SYSTEM_ADMIN_KEY:
        conn = get_db()
        conn.execute("DELETE FROM schools WHERE school_code = ?", (school_code,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "School removed"})
    return jsonify({"success": False, "message": "Unauthorized"}), 401


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        sc = request.form.get("school_code", "").strip().lower()
        un = request.form.get("username", "").strip().lower()
        pw = request.form.get("password", "")

        auth, err = authenticate_user(sc, un, pw)
        if err:
            flash(err, "danger")
            return redirect(url_for("login"))

        session["school_id"] = auth["school"]["id"]
        session["school_name"] = auth["school"]["school_name"]
        session["username"] = auth["teacher"]["username"]
        session["role"] = auth["teacher"].get("role", "teacher")
        return redirect(url_for("dashboard"))
    return render_template("cloud_login.html")


@app.route("/dashboard")
def dashboard():
    if "school_id" not in session:
        return redirect(url_for("login"))
    return render_template("cloud_dashboard.html", grades=GRADE_OPTIONS)


@app.route("/marks/<grade>", methods=["GET", "POST"])
def enter_marks(grade):
    if "school_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    subjects = GRADE_SUBJECTS.get(grade, [])
    students = conn.execute(
        "SELECT * FROM students WHERE school_id = ? AND grade = ?",
        (session["school_id"], grade),
    ).fetchall()
    exam_title = request.args.get("exam_title", EXAM_TITLE_DEFAULT)

    if request.method == "POST":
        now = datetime.utcnow().isoformat()
        for s in students:
            adm = s["adm_no"]
            scores = {
                sub: {
                    "score": request.form.get(f"score_{adm}_{sub}"),
                    "rating": request.form.get(f"rating_{adm}_{sub}"),
                }
                for sub in subjects
            }
            conn.execute(
                """
                INSERT INTO marks (school_id, grade, adm_no, student_name, exam_title, subject_scores_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(school_id, grade, adm_no, exam_title) DO UPDATE SET
                subject_scores_json = excluded.subject_scores_json, updated_at = excluded.updated_at
            """,
                (
                    session["school_id"],
                    grade,
                    adm,
                    s["student_name"],
                    exam_title,
                    json.dumps(scores),
                    now,
                ),
            )
        conn.commit()
        flash("Marks saved successfully.", "success")

    marks = conn.execute(
        "SELECT * FROM marks WHERE school_id = ? AND grade = ? AND exam_title = ?",
        (session["school_id"], grade, exam_title),
    ).fetchall()
    conn.close()
    marks_map = {row["adm_no"]: json.loads(row["subject_scores_json"]) for row in marks}
    return render_template(
        "cloud_marks.html",
        grade=grade,
        subjects=subjects,
        students=students,
        marks_map=marks_map,
        exam_title=exam_title,
    )


@app.route("/students/<grade>")
def manage_students(grade):
    if "school_id" not in session:
        return redirect(url_for("login"))

    # Teachers can view the list, but there is no 'POST' to add/delete
    conn = get_db()
    students = conn.execute(
        "SELECT * FROM students WHERE school_id = ? AND grade = ? ORDER BY student_name ASC",
        (session["school_id"], grade),
    ).fetchall()
    conn.close()

    return render_template("cloud_students.html", grade=grade, students=students)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    # Crucial for Railway: Listen on 0.0.0.0 and use the dynamic PORT variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
