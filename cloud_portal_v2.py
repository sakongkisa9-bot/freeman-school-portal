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

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(PROJECT_DIR, "templates")
app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-2026")


@app.before_request
def log_request_info():
    # This prints to your Railway "Deployments > View Logs" tab
    app.logger.debug("Headers: %s", request.headers)
    app.logger.debug("Body: %s", request.get_data())
    print(f"DEBUG: Request received at {request.path} from {request.remote_addr}")


from functools import wraps

DB_PATH = "/data/freeman_cloud.db"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

EXAM_TITLE_DEFAULT = "TERM 1 EXAM 2026"

GRADE_OPTIONS = [
    "playgroup",
    "pp1",
    "pp2",
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
    "playgroup": ["LANG", "MATH", "ENV", "CREAT"],
    "pp1": ["LANG", "MATH", "ENV", "PSYCH", "REL"],
    "pp2": ["LANG", "MATH", "ENV", "PSYCH", "REL"],
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
    conn = sqlite3.connect(DB_PATH, timeout=10)
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
    # Normalize school_code to lowercase to match your register logic
    sc = school_code.strip().lower()
    school = conn.execute(
        "SELECT * FROM schools WHERE school_code = ?", (sc,)
    ).fetchone()

    if not school:
        conn.close()
        return None, "School code not found."

    teacher = conn.execute(
        "SELECT * FROM teachers WHERE school_id = ? AND username = ?",
        (school["id"], username.strip().lower()),  # Use [] instead of .get()
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
    return render_template("cloud_register.html", admin_key=SYSTEM_ADMIN_KEY)


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
    try:
        if request.method == "POST":
            sc = request.form.get("school_code", "").strip().lower()
            un = request.form.get("username", "").strip().lower()
            pw = request.form.get("password", "")

            auth, err = authenticate_user(sc, un, pw)
            if err:
                flash(err, "danger")
                return redirect(url_for("login"))

            # --- THE FIX IS HERE ---
            # Convert the Row objects to real dictionaries so .get() works elsewhere
            school_data = dict(auth["school"])
            teacher_data = dict(auth["teacher"])

            session["school_id"] = school_data["id"]
            session["school_name"] = school_data["school_name"]
            session["username"] = teacher_data["username"]
            session["role"] = teacher_data.get("role", "teacher")  # .get() works now!

            return redirect(url_for("dashboard"))

    except Exception as e:
        # This will tell us exactly which key is missing if it happens again
        return f"Database Error: {str(e)}"

    return render_template("cloud_login.html")


@app.route("/dashboard")
def dashboard():
    if "school_id" not in session:
        return redirect(url_for("login"))
    return render_template("cloud_dashboard.html", grades=GRADE_OPTIONS)


@app.route("/api/sync_students", methods=["POST"])
@app.route("/api/upload_students", methods=["POST"])
def api_sync_students():
    data = request.json
    school_code = data.get("school_code").strip().lower()
    students_list = data.get("students", [])

    if not school_code:
        return jsonify({"success": False, "message": "Missing school code"}), 400

    conn = get_db()
    try:
        # 1. Verify the school exists
        school = conn.execute(
            "SELECT id FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()
        if not school:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"School code '{school_code}' not registered on cloud.",
                    }
                ),
                404,
            )
        school_id = school["id"]
        # 2. Insert/Update students
        for s in students_list:
            conn.execute(
                """
                INSERT INTO students (school_id, grade, adm_no, student_name, gender, phone)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(school_id, grade, adm_no) DO UPDATE SET
                    student_name = excluded.student_name,
                    gender = excluded.gender,
                    phone = excluded.phone
            """,
                (
                    school_id,
                    s["grade"],
                    s["adm_no"],
                    s["name"],
                    s.get("gender"),
                    s.get("phone"),
                ),
            )

        conn.commit()
        return jsonify(
            {
                "success": True,
                "message": f"Successfully synced {len(students_list)} students.",
            }
        )

    except Exception as e:
        logging.error(f"Sync error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/marks/<grade>/<subject>", methods=["GET", "POST"])
def enter_marks(grade, subject):
    if "school_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    # Fetch students for this grade
    students = conn.execute(
        "SELECT * FROM students WHERE school_id = ? AND grade = ? ORDER BY student_name ASC",
        (session["school_id"], grade),
    ).fetchall()

    exam_title = request.args.get("exam_title", EXAM_TITLE_DEFAULT)

    if request.method == "POST":
        now = datetime.utcnow().isoformat()
        for s in students:
            adm = s["adm_no"]
            score = request.form.get(f"score_{adm}")

            # 1. Get existing marks first so we don't overwrite other subjects
            existing = conn.execute(
                "SELECT subject_scores_json FROM marks WHERE school_id=? AND grade=? AND adm_no=? AND exam_title=?",
                (session["school_id"], grade, adm, exam_title),
            ).fetchone()

            scores = json.loads(existing["subject_scores_json"]) if existing else {}

            # 2. Update only the specific subject being edited
            scores[subject] = {"score": score}

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
        flash(f"Marks for {subject} saved successfully.", "success")

    # Fetch existing marks to display in the input boxes
    marks_records = conn.execute(
        "SELECT adm_no, subject_scores_json FROM marks WHERE school_id=? AND grade=? AND exam_title=?",
        (session["school_id"], grade, exam_title),
    ).fetchall()
    conn.close()

    # Map scores so the HTML can find them: marks_map[adm_no] = score_value
    marks_map = {}
    for row in marks_records:
        data = json.loads(row["subject_scores_json"])
        if subject in data:
            marks_map[row["adm_no"]] = data[subject].get("score", "")

    return render_template(
        "cloud_marks.html",
        grade=grade,
        subject=subject,
        students=students,
        marks_map=marks_map,
        exam_title=exam_title,
    )


@app.route("/select_subject/<grade>")
def select_subject(grade):
    if "school_id" not in session:
        return redirect(url_for("login"))

    # Get the subjects for this grade from your dictionary
    subjects = GRADE_SUBJECTS.get(grade, [])

    if not subjects:
        flash(f"No subjects configured for {grade}.", "warning")
        return redirect(url_for("dashboard"))

    return render_template("cloud_select_subject.html", grade=grade, subjects=subjects)


@app.route("/api/get_marks", methods=["POST"])
def api_get_marks():
    data = request.json
    sc = data.get("school_code", "").strip().lower()
    gr = data.get("grade")

    conn = get_db()
    # 1. Find school
    school = conn.execute(
        "SELECT id FROM schools WHERE school_code=?", (sc,)
    ).fetchone()

    if not school:
        return jsonify({"success": False, "message": "School not found"}), 404

    # 2. Get marks for that grade
    rows = conn.execute(
        "SELECT * FROM marks WHERE school_id = ? AND grade = ?", (school["id"], gr)
    ).fetchall()
    print(f"DEBUG: Found {len(rows)} marks in DB for school {sc} grade {gr}")
    # 3. Package them up
    marks_list = []
    for r in rows:
        marks_list.append(
            {
                "adm_no": r["adm_no"],
                "student_name": r["student_name"],
                "grade": r["grade"],
                "exam_title": r["exam_title"],
                "scores": json.loads(r["subject_scores_json"]),
            }
        )

    # Return with the key 'marks'
    return jsonify({"success": True, "marks": marks_list})


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
