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
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

DB_PATH = os.path.join(PROJECT_DIR, "cloud_portal.db")

# Configure logging
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
    "Playgroup": ["LANG", "MATH", "CREAT", "ENV"],
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parent_view_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            content_type TEXT NOT NULL,
            content_id INTEGER NOT NULL,
            has_viewed INTEGER DEFAULT 0,
            viewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, content_type, content_id),
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)
    conn.commit()
    # Migration handling
    try:
        cursor.execute("ALTER TABLE teachers ADD COLUMN email TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN gender TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN phone TEXT")
    except Exception:
        pass
    conn.commit()
    conn.close()


def get_school_by_code(school_code):
    conn = None
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()
        return row
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_teacher(school_id, username):
    conn = None
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM teachers WHERE school_id = ? AND username = ?",
            (school_id, username),
        ).fetchone()
        return row
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()


def authenticate_user(school_code, username, password):
    school = get_school_by_code(school_code)
    if not school:
        return None, "School code not found."
    teacher = get_teacher(school["id"], username)
    if not teacher or not check_password_hash(teacher["password_hash"], password):
        return None, "Invalid username or password."
    return {"school": school, "teacher": teacher}, None


def is_admin():
    return session.get("role") == "admin"


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "school_id" not in session:
            return redirect(url_for("login"))
        if not is_admin():
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)

    return wrapper


def get_students_for_grade(school_id, grade):
    conn = None
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM students WHERE school_id = ? AND grade = ? ORDER BY adm_no",
            (school_id, grade),
        ).fetchall()
        return rows
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_marks_for_grade(school_id, grade, exam_title):
    conn = None
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM marks WHERE school_id = ? AND grade = ? AND exam_title = ? ORDER BY adm_no",
            (school_id, grade, exam_title),
        ).fetchall()
        return rows
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def save_marks_records(school_id, grade, exam_title, records):
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    for item in records:
        student_name = item.get("name", "")
        adm_no = item.get("adm_no", "")
        subject_scores_json = json.dumps(item.get("scores", {}))
        total_points = item.get("total_points", "")
        average_level = item.get("average_level", "")
        cursor.execute(
            """
            INSERT INTO marks (school_id, grade, adm_no, student_name, exam_title, subject_scores_json, total_points, average_level, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(school_id, grade, adm_no, exam_title) DO UPDATE SET
                student_name = excluded.student_name,
                subject_scores_json = excluded.subject_scores_json,
                total_points = excluded.total_points,
                average_level = excluded.average_level,
                updated_at = excluded.updated_at
        """,
            (
                school_id,
                grade,
                adm_no,
                student_name,
                exam_title,
                subject_scores_json,
                total_points,
                average_level,
                now,
            ),
        )
    conn.commit()
    conn.close()


def save_students_records(school_id, students):
    conn = get_db()
    cursor = conn.cursor()
    for item in students:
        student_name = item.get("name", "")
        adm_no = item.get("adm_no", "")
        grade = item.get("grade", "")
        gender = item.get("gender", "")
        phone = item.get("phone", "")
        if not (student_name and adm_no and grade):
            continue
        cursor.execute(
            """
            INSERT INTO students (school_id, grade, adm_no, student_name, gender, phone)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(school_id, grade, adm_no) DO UPDATE SET
                student_name = excluded.student_name,
                gender = excluded.gender,
                phone = excluded.phone
        """,
            (school_id, grade, adm_no, student_name, gender, phone),
        )
    conn.commit()
    conn.close()


def get_all_schools():
    conn = None
    try:
        conn = get_db()
        return conn.execute("SELECT * FROM schools ORDER BY created_at DESC").fetchall()
    except sqlite3.Error:
        return []
    finally:
        if conn:
            conn.close()


def delete_school_by_code(school_code):
    conn = None
    try:
        conn = get_db()
        conn.execute("BEGIN")
        row = conn.execute(
            "SELECT id FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()
        if not row:
            return False
        sid = row["id"]
        conn.execute("DELETE FROM marks WHERE school_id = ?", (sid,))
        conn.execute("DELETE FROM students WHERE school_id = ?", (sid,))
        conn.execute("DELETE FROM teachers WHERE school_id = ?", (sid,))
        conn.execute("DELETE FROM schools WHERE id = ?", (sid,))
        conn.commit()
        return True
    except Exception:
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


# Start DB
init_db()


@app.route("/")
def home():
    return render_template("cloud_home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        sn = request.form.get("school_name", "").strip()
        sc = request.form.get("school_code", "").strip().lower()
        se = request.form.get("email", "").strip()
        un = request.form.get("username", "").strip().lower()
        te = request.form.get("teacher_email", "").strip().lower()
        pw = request.form.get("password", "")

        if not sn or not sc or not un or not pw:
            flash("Required fields missing.", "danger")
            return redirect(url_for("register"))

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
            conn.execute(
                "INSERT INTO teachers (school_id, username, password_hash, email, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (row["id"], un, ph, te, "admin", now),
            )
            conn.commit()
            flash("Registered! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Code already exists.", "danger")
        finally:
            conn.close()
    return render_template("cloud_register.html")


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


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/parent_login", methods=["GET", "POST"])
def parent_login():
    if request.method == "POST":
        school_name = request.form.get("school_name", "").strip()
        student_name = request.form.get("student_name", "").strip()
        adm_no = request.form.get("adm_no", "").strip()
        
        if not school_name or not student_name or not adm_no:
            flash("All fields are required.", "danger")
            return redirect(url_for("parent_login"))
        
        # Find school by name
        conn = get_db()
        try:
            school = conn.execute(
                "SELECT * FROM schools WHERE LOWER(school_name) = LOWER(?)",
                (school_name,)
            ).fetchone()
            
            if not school:
                flash("School not found.", "danger")
                return redirect(url_for("parent_login"))
            
            # Find student
            student = conn.execute(
                "SELECT * FROM students WHERE school_id = ? AND LOWER(student_name) = LOWER(?) AND adm_no = ?",
                (school["id"], student_name, adm_no)
            ).fetchone()
            
            if not student:
                flash("Student not found. Please check the details.", "danger")
                return redirect(url_for("parent_login"))
            
            # Set session for parent
            session["school_id"] = school["id"]
            session["school_name"] = school["school_name"]
            session["student_id"] = student["id"]
            session["student_name"] = student["student_name"]
            session["student_grade"] = student["grade"]
            session["student_adm_no"] = student["adm_no"]
            session["role"] = "parent"
            
            return redirect(url_for("parent_dashboard"))
            
        finally:
            conn.close()
    
    return render_template("cloud_parent_login.html")


@app.route("/parent_dashboard")
def parent_dashboard():
    if "role" not in session or session["role"] != "parent":
        return redirect(url_for("parent_login"))
    
    # Check for unread notifications
    conn = get_db()
    try:
        student_id = session.get("student_id")
        
        # Check unread newsletters
        unread_newsletters = conn.execute("""
            SELECT COUNT(*) as count FROM parent_view_status
            WHERE student_id = ? AND content_type = 'newsletter' AND has_viewed = 0
        """, (student_id,)).fetchone()["count"]
        
        # Check unread reports (assuming reports have content_type 'report')
        unread_reports = conn.execute("""
            SELECT COUNT(*) as count FROM parent_view_status
            WHERE student_id = ? AND content_type = 'report' AND has_viewed = 0
        """, (student_id,)).fetchone()["count"]
        
        return render_template(
            "cloud_parent_landing.html",
            school_name=session.get("school_name"),
            student_name=session.get("student_name"),
            student_grade=session.get("student_grade"),
            student_adm_no=session.get("student_adm_no"),
            unread_newsletters=unread_newsletters,
            unread_reports=unread_reports
        )
    finally:
        conn.close()


@app.route("/parent_report")
def parent_report():
    if "role" not in session or session["role"] != "parent":
        return redirect(url_for("parent_login"))
    
    # This will show the existing report - we'll need to adapt the existing dashboard
    return render_template(
        "cloud_parent_dashboard.html",
        school_name=session.get("school_name"),
        student_name=session.get("student_name"),
        student_grade=session.get("student_grade"),
        student_adm_no=session.get("student_adm_no")
    )


@app.route("/parent_newsletters")
def parent_newsletters():
    if "role" not in session or session["role"] != "parent":
        return redirect(url_for("parent_login"))
    
    # Get newsletters for this parent's student class
    conn = get_db()
    try:
        student_grade = session.get("student_grade")
        student_id = session.get("student_id")
        
        # Get newsletters from portal_announcements table with view status
        newsletters = conn.execute("""
            SELECT pa.*, n.attachment_path,
                   COALESCE(pvs.has_viewed, 0) as has_viewed
            FROM portal_announcements pa
            LEFT JOIN newsletters n ON pa.newsletter_id = n.id
            LEFT JOIN parent_view_status pvs ON pvs.content_id = pa.id 
                AND pvs.content_type = 'newsletter' 
                AND pvs.student_id = ?
            WHERE pa.class_context = ? OR pa.class_context = 'All Classes'
            ORDER BY pa.published_at DESC
        """, (student_id, student_grade)).fetchall()
        
        return render_template(
            "cloud_parent_newsletters.html",
            newsletters=newsletters,
            school_name=session.get("school_name"),
            student_name=session.get("student_name")
        )
    finally:
        conn.close()


@app.route("/mark_newsletter_viewed/<int:newsletter_id>", methods=["POST"])
def mark_newsletter_viewed(newsletter_id):
    if "role" not in session or session["role"] != "parent":
        return jsonify({"success": False}), 401
    
    conn = get_db()
    try:
        student_id = session.get("student_id")
        
        # Mark as viewed
        conn.execute("""
            INSERT OR REPLACE INTO parent_view_status 
            (student_id, content_type, content_id, has_viewed, viewed_at)
            VALUES (?, 'newsletter', ?, 1, CURRENT_TIMESTAMP)
        """, (student_id, newsletter_id))
        
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@app.route("/dashboard")
def dashboard():
    if "school_id" not in session:
        return redirect(url_for("login"))
    return render_template(
        "cloud_dashboard.html",
        school_name=session.get("school_name"),
        username=session.get("username"),
        grades=GRADE_OPTIONS,
    )


@app.route("/students/<grade>", methods=["GET", "POST"])
def manage_students(grade):
    if "school_id" not in session:
        return redirect(url_for("login"))
    if not is_admin():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("student_name", "").strip()
        adm = request.form.get("adm_no", "").strip()
        gen = request.form.get("gender", "").strip()
        ph = request.form.get("phone", "").strip()
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO students (school_id, grade, adm_no, student_name, gender, phone) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO UPDATE SET student_name=excluded.student_name",
                (session["school_id"], grade, adm, name, gen, ph),
            )
            conn.commit()
            flash("Student updated.", "success")
        finally:
            conn.close()
    students = get_students_for_grade(session["school_id"], grade)
    return render_template("cloud_students.html", grade=grade, students=students)


@app.route("/marks/<grade>", methods=["GET", "POST"])
def enter_marks(grade):
    if "school_id" not in session:
        return redirect(url_for("login"))
    subjects = GRADE_SUBJECTS.get(grade, [])
    students = get_students_for_grade(session["school_id"], grade)
    exam_title = request.args.get("exam_title", EXAM_TITLE_DEFAULT)
    if request.method == "POST":
        recs = []
        for s in students:
            adm = s["adm_no"]
            scores = {
                sub: {
                    "score": request.form.get(f"score_{adm}_{sub}"),
                    "rating": request.form.get(f"rating_{adm}_{sub}"),
                }
                for sub in subjects
            }
            recs.append({"adm_no": adm, "name": s["student_name"], "scores": scores})
        save_marks_records(
            session["school_id"],
            grade,
            request.form.get("exam_title", EXAM_TITLE_DEFAULT),
            recs,
        )
        flash("Saved.", "success")
    marks = get_marks_for_grade(session["school_id"], grade, exam_title)
    marks_map = {row["adm_no"]: json.loads(row["subject_scores_json"]) for row in marks}
    return render_template(
        "cloud_marks.html",
        grade=grade,
        subjects=subjects,
        students=students,
        marks_map=marks_map,
        exam_title=exam_title,
    )


# API Routes
@app.route("/api/fetch_marks", methods=["POST"])
def api_fetch_marks():
    data = request.get_json(force=True)
    auth, err = authenticate_user(
        data.get("school_code"), data.get("username"), data.get("password")
    )
    if err:
        return jsonify({"success": False, "message": err}), 401
    grade = data.get("grade")
    students = get_students_for_grade(auth["school"]["id"], grade)
    marks = get_marks_for_grade(
        auth["school"]["id"], grade, data.get("exam_title", EXAM_TITLE_DEFAULT)
    )
    marks_map = {row["adm_no"]: json.loads(row["subject_scores_json"]) for row in marks}
    records = [
        {
            "adm_no": s["adm_no"],
            "name": s["student_name"],
            "scores": marks_map.get(s["adm_no"], {}),
        }
        for s in students
    ]
    return jsonify(
        {"success": True, "records": records, "subjects": GRADE_SUBJECTS.get(grade, [])}
    )


@app.route("/api/save_marks", methods=["POST"])
def api_save_marks():
    data = request.get_json(force=True)
    auth, err = authenticate_user(
        data.get("school_code"), data.get("username"), data.get("password")
    )
    if err:
        return jsonify({"success": False, "message": err}), 401
    save_marks_records(
        auth["school"]["id"],
        data.get("grade"),
        data.get("exam_title"),
        data.get("records", []),
    )
    return jsonify({"success": True})


@app.route("/api/upload_students", methods=["POST"])
def api_upload_students():
    data = request.get_json(force=True)
    auth, err = authenticate_user(
        data.get("school_code"), data.get("username"), data.get("password")
    )
    if err:
        return jsonify({"success": False, "message": err}), 401
    save_students_records(auth["school"]["id"], data.get("students", []))
    return jsonify({"success": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7000))
    app.run(host="0.0.0.0", port=port)
