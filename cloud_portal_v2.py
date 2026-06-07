from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    send_from_directory,
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import json
from datetime import datetime
import logging
from grading_logic import get_grade_7_8_rating, get_grade_4_6_rating, calculate_final_level

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(PROJECT_DIR, "templates")
app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-2026")

# Custom Jinja2 filter to convert numerical score to rating
def score_to_rating(score, grade):
    """Convert numerical score to rating based on grade level"""
    try:
        s = float(score)
        if not s or s == 0:
            return "BE2"
        
        # For playgroup, pp1, pp2, use the rating system
        grade_lower = grade.lower() if grade else ""
        if grade_lower in ["playgroup", "pp1", "pp2"]:
            # Use the same rating logic as Grade 4-6
            if s >= 90: return "EE1"
            elif s >= 75: return "EE2"
            elif s >= 58: return "ME1"
            elif s >= 41: return "ME2"
            elif s >= 31: return "AE1"
            elif s >= 21: return "AE2"
            elif s >= 11: return "BE1"
            else: return "BE2"
        elif grade_lower in ["grade 1", "grade 2", "grade 3"]:
            # Primary grades
            if s >= 90: return "EE1"
            elif s >= 75: return "EE2"
            elif s >= 58: return "ME1"
            elif s >= 41: return "ME2"
            elif s >= 31: return "AE1"
            elif s >= 21: return "AE2"
            elif s >= 11: return "BE1"
            else: return "BE2"
        elif grade_lower in ["grade 4", "grade 5", "grade 6"]:
            # Primary grades with different scale
            if s >= 90: return "EE1"
            elif s >= 75: return "EE2"
            elif s >= 58: return "ME1"
            elif s >= 41: return "ME2"
            elif s >= 31: return "AE1"
            elif s >= 21: return "AE2"
            elif s >= 11: return "BE1"
            else: return "BE2"
        elif grade_lower in ["grade 7", "grade 8", "grade 9"]:
            # Junior Secondary
            if s >= 90: return "EE1"
            elif s >= 75: return "EE2"
            elif s >= 58: return "ME1"
            elif s >= 41: return "ME2"
            elif s >= 31: return "AE1"
            elif s >= 21: return "AE2"
            elif s >= 11: return "BE1"
            else: return "BE2"
        else:
            # Default
            if s >= 90: return "EE1"
            elif s >= 75: return "EE2"
            elif s >= 58: return "ME1"
            elif s >= 41: return "ME2"
            elif s >= 31: return "AE1"
            elif s >= 21: return "AE2"
            elif s >= 11: return "BE1"
            else: return "BE2"
    except:
        return "BE2"

# Custom Jinja2 filter to convert rating to points for comparison
def rating_to_points(rating):
    """Convert rating to points for comparison"""
    rating_points = {
        "EE1": 8,
        "EE2": 7,
        "ME1": 6,
        "ME2": 5,
        "AE1": 4,
        "AE2": 3,
        "BE1": 2,
        "BE2": 1
    }
    return rating_points.get(rating, 0)

# Custom Jinja2 filter to convert rating to teacher comment
def rating_to_comment(rating):
    """Convert rating to teacher comment based on performance level"""
    rating_comments = {
        "BE1": "A starting point. Focus on understanding the basic concepts, and I am here to help you practice.",
        "BE2": "You are showing effort, but need more practice on the fundamentals to reach the expected level.",
        "ME1": "Good progress. You are grasping the core ideas; continue practicing to gain more confidence.",
        "ME2": "Well done! You are very close to mastering this. Pay close attention to the finer details.",
        "EE1": "Great work! You have successfully demonstrated this competency. Keep up the consistent performance.",
        "EE2": "Outstanding! You have mastered the task and shown deep understanding. Keep challenging yourself."
    }
    return rating_comments.get(rating, "No comment available.")

# Custom Jinja2 filter to get class teacher comment based on average level
def get_class_teacher_comment(average_level):
    """Get class teacher comment based on average level"""
    comments = {
        "EE1": "Outstanding performance! You have shown a deep and advanced understanding of all subjects.",
        "EE2": "Excellent work! You are consistently performing at a very high level. Keep it up!",
        "ME1": "Good work! You have a solid grasp of the core concepts. Keep up the steady progress.",
        "ME2": "Good effort! You are making steady progress and engaging well with your lessons.",
        "AE1": "You are making progress. Focus on the finer details to reach full mastery.",
        "AE2": "A promising performance. Keep practicing to strengthen your understanding of these topics.",
        "BE1": "You are starting to grasp the basics. Let's keep working together to build your confidence.",
        "BE2": "A beginning step in your learning journey. Stay dedicated, and we will work on the fundamentals."
    }
    return comments.get(average_level, "No comment available.")

# Custom Jinja2 filter to get head teacher comment based on average level
def get_head_teacher_comment(average_level):
    """Get head teacher comment based on average level"""
    comments = {
        "EE1": "Excellent achievement. Continue to maintain this high standard of excellence.",
        "EE2": "A remarkable performance this term. Well done on your hard work.",
        "ME1": "You are meeting expectations well. Continue to be consistent in your studies.",
        "ME2": "You are performing well. Keep up the consistency as you prepare for the next term.",
        "AE1": "Good effort shown. With more focus, I am confident you will meet expectations soon.",
        "AE2": "You are close to the target level. Keep working hard and stay focused.",
        "BE1": "I see potential in your work. Let's strive to meet the expected goals next term.",
        "BE2": "There is potential for growth. We will provide the support needed to improve next term."
    }
    return comments.get(average_level, "No comment available.")

# Custom Jinja2 filter to convert image file to base64
def image_to_base64(image_path):
    """Convert image file to base64 data URL"""
    if not image_path:
        return ""
    import base64
    import os
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode('utf-8')
                # Determine file extension
                ext = os.path.splitext(image_path)[1].lower()
                mime_type = "image/png" if ext == ".png" else "image/jpeg"
                return f"data:{mime_type};base64,{encoded}"
        else:
            return ""
    except Exception as e:
        logging.error(f"Error converting image to base64: {e}")
        return ""

# Custom Jinja2 filter to convert points to rating
def points_to_rating(points):
    """Convert points back to rating"""
    if points >= 7.5: return "EE1"
    elif points >= 6.5: return "EE2"
    elif points >= 5.5: return "ME1"
    elif points >= 4.5: return "ME2"
    elif points >= 3.5: return "AE1"
    elif points >= 2.5: return "AE2"
    elif points >= 1.5: return "BE1"
    else: return "BE2"

app.jinja_env.filters['score_to_rating'] = score_to_rating
app.jinja_env.filters['rating_to_points'] = rating_to_points
app.jinja_env.filters['points_to_rating'] = points_to_rating
app.jinja_env.filters['rating_to_comment'] = rating_to_comment
app.jinja_env.filters['get_class_teacher_comment'] = get_class_teacher_comment
app.jinja_env.filters['get_head_teacher_comment'] = get_head_teacher_comment
app.jinja_env.filters['image_to_base64'] = image_to_base64


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
            portal_open INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            school_address TEXT,
            school_telephone TEXT,
            school_logo TEXT
        )
    """)
    # Add portal_open column if it doesn't exist (for existing databases)
    cursor.execute("PRAGMA table_info(schools)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'portal_open' not in columns:
        cursor.execute("ALTER TABLE schools ADD COLUMN portal_open INTEGER DEFAULT 0")
        conn.commit()
    else:
        # Update existing schools to have portal_open = 0 (closed) by default
        cursor.execute("UPDATE schools SET portal_open = 0 WHERE portal_open IS NULL")
        conn.commit()
    
    # Add school details columns if they don't exist
    cursor.execute("PRAGMA table_info(schools)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'school_address' not in columns:
        cursor.execute("ALTER TABLE schools ADD COLUMN school_address TEXT")
        conn.commit()
    if 'school_telephone' not in columns:
        cursor.execute("ALTER TABLE schools ADD COLUMN school_telephone TEXT")
        conn.commit()
    if 'school_logo' not in columns:
        cursor.execute("ALTER TABLE schools ADD COLUMN school_logo TEXT")
        conn.commit()
    if 'school_administrator' not in columns:
        cursor.execute("ALTER TABLE schools ADD COLUMN school_administrator TEXT")
        conn.commit()
    if 'school_signature' not in columns:
        cursor.execute("ALTER TABLE schools ADD COLUMN school_signature TEXT")
        conn.commit()
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
            photo TEXT,
            stream TEXT,
            UNIQUE(school_id, grade, adm_no),
            FOREIGN KEY(school_id) REFERENCES schools(id)
        )
    """)
    # Add photo column if it doesn't exist
    cursor.execute("PRAGMA table_info(students)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'photo' not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN photo TEXT")
        conn.commit()
    # Add stream column if it doesn't exist
    if 'stream' not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN stream TEXT")
        conn.commit()
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
        CREATE TABLE IF NOT EXISTS teacher_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            class_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            teacher_name TEXT NOT NULL,
            teacher_code TEXT NOT NULL,
            UNIQUE(school_id, class_name, subject),
            FOREIGN KEY(school_id) REFERENCES schools(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            adm_no TEXT NOT NULL,
            grade TEXT NOT NULL,
            school_name TEXT NOT NULL,
            report_data TEXT NOT NULL,
            generated_date TEXT NOT NULL,
            UNIQUE(student_name, adm_no, school_name, generated_date)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS previous_exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_name TEXT,
            class_name TEXT,
            exam_date TEXT,
            summary_data TEXT,
            marks_data TEXT,
            UNIQUE(exam_name, class_name)
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fcm_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            device_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, token),
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS newsletters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            target_type TEXT,
            class_context TEXT,
            recipient_role TEXT,
            attachment_path TEXT,
            send_email INTEGER DEFAULT 0,
            send_sms INTEGER DEFAULT 0,
            is_draft INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portal_announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            newsletter_id INTEGER,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            target_type TEXT,
            class_context TEXT NOT NULL,
            recipient_role TEXT,
            attachment_path TEXT,
            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(newsletter_id) REFERENCES newsletters(id)
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
    # Show role selection page
    return render_template("cloud_home.html")


@app.route("/firebase-messaging-sw.js")
def serve_firebase_sw():
    """Serve the Firebase Cloud Messaging service worker"""
    return send_from_directory('static', 'firebase-messaging-sw.js')


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
            return redirect(url_for("teacher_login"))
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


@app.route("/admin/schools")
def admin_schools():
    # Admin page to view and manage all registered schools
    conn = get_db()
    schools = conn.execute("SELECT * FROM schools ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template("cloud_admin_schools.html", schools=schools)


@app.route("/admin/schools/<school_code>/delete", methods=["POST"])
def admin_delete_school(school_code):
    # Delete a school and all its data
    conn = get_db()
    try:
        # Delete marks first
        conn.execute("DELETE FROM marks WHERE school_id = (SELECT id FROM schools WHERE school_code = ?)", (school_code,))
        # Delete students
        conn.execute("DELETE FROM students WHERE school_id = (SELECT id FROM schools WHERE school_code = ?)", (school_code,))
        # Delete teachers
        conn.execute("DELETE FROM teachers WHERE school_id = (SELECT id FROM schools WHERE school_code = ?)", (school_code,))
        # Delete school
        conn.execute("DELETE FROM schools WHERE school_code = ?", (school_code,))
        conn.commit()
        flash(f"School '{school_code}' deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting school: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("admin_schools"))


@app.route("/admin/schools/<school_code>/edit", methods=["GET", "POST"])
def admin_edit_school(school_code):
    # Edit school details
    conn = get_db()
    if request.method == "POST":
        try:
            school_name = request.form.get("school_name", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            school_administrator = request.form.get("school_administrator", "").strip()
            signature_file = request.files.get("signature")

            if not school_name:
                flash("School name is required.", "danger")
                return redirect(url_for("admin_edit_school", school_code=school_code))

            # Convert signature to base64 if uploaded
            signature_base64 = None
            if signature_file and signature_file.filename:
                import base64
                signature_data = signature_file.read()
                signature_base64 = base64.b64encode(signature_data).decode('utf-8')
                # Determine mime type
                ext = signature_file.filename.lower().split('.')[-1]
                mime_type = "image/png" if ext == "png" else "image/jpeg"
                signature_base64 = f"data:{mime_type};base64,{signature_base64}"

            if password:
                # Update password if provided
                password_hash = generate_password_hash(password)
                conn.execute(
                    "UPDATE schools SET school_name = ?, email = ?, password_hash = ?, school_administrator = ? WHERE school_code = ?",
                    (school_name, email, password_hash, school_administrator, school_code)
                )
            else:
                # Update only name and email
                conn.execute(
                    "UPDATE schools SET school_name = ?, email = ?, school_administrator = ? WHERE school_code = ?",
                    (school_name, email, school_administrator, school_code)
                )

            # Update signature if uploaded
            if signature_base64:
                conn.execute(
                    "UPDATE schools SET school_signature = ? WHERE school_code = ?",
                    (signature_base64, school_code)
                )

            conn.commit()
            flash(f"School '{school_code}' updated successfully.", "success")
            return redirect(url_for("admin_schools"))
        except Exception as e:
            conn.rollback()
            flash(f"Error updating school: {e}", "danger")
        finally:
            conn.close()
    else:
        school = conn.execute("SELECT * FROM schools WHERE school_code = ?", (school_code,)).fetchone()
        conn.close()
        if not school:
            flash("School not found.", "danger")
            return redirect(url_for("admin_schools"))
        return render_template("cloud_edit_school.html", school=school)


@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    try:
        if request.method == "POST":
            sc = request.form.get("school_code", "").strip().lower()
            un = request.form.get("username", "").strip().lower()
            pw = request.form.get("password", "")
            teacher_code = request.form.get("teacher_code", "").strip()

            auth, err = authenticate_user(sc, un, pw)
            if err:
                flash(err, "danger")
                return redirect(url_for("teacher_login"))

            # --- THE FIX IS HERE ---
            # Convert the Row objects to real dictionaries so .get() works elsewhere
            school_data = dict(auth["school"])
            teacher_data = dict(auth["teacher"])

            # Verify teacher code exists in teacher_assignments
            conn = get_db()
            teacher_assignment = conn.execute(
                "SELECT * FROM teacher_assignments WHERE school_id = ? AND teacher_code = ?",
                (school_data["id"], teacher_code)
            ).fetchone()
            conn.close()

            if not teacher_assignment:
                flash("Teacher code does not exist. Please contact your administrator.", "danger")
                return redirect(url_for("teacher_login"))

            session["school_id"] = school_data["id"]
            session["school_name"] = school_data["school_name"]
            session["username"] = teacher_data["username"]
            session["role"] = teacher_data.get("role", "teacher")  # .get() works now!
            session["teacher_code"] = teacher_code  # Store teacher code for later verification

            return redirect(url_for("dashboard"))

    except Exception as e:
        # This will tell us exactly which key is missing if it happens again
        return f"Database Error: {str(e)}"

    return render_template("cloud_login.html")


@app.route("/dashboard")
def dashboard():
    if "school_id" not in session:
        return redirect(url_for("teacher_login"))

    conn = get_db()
    school = conn.execute(
        "SELECT portal_open FROM schools WHERE id = ?", (session["school_id"],)
    ).fetchone()
    conn.close()

    portal_open = school["portal_open"] if school else 1
    return render_template("cloud_dashboard.html", grades=GRADE_OPTIONS, portal_open=portal_open)


@app.route("/api/toggle_portal", methods=["POST"])
def api_toggle_portal():
    # API key authentication (like sync endpoints)
    data = request.json
    school_code = data.get("school_code", "").strip().lower()
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    if not school_code or not username or not password:
        return jsonify({"success": False, "message": "Missing credentials"}), 400

    conn = get_db()
    try:
        # Authenticate school and user
        school = conn.execute(
            "SELECT * FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()

        if not school:
            return jsonify({"success": False, "message": "School not found"}), 404

        # Verify password
        if not check_password_hash(school["password_hash"], password):
            return jsonify({"success": False, "message": "Invalid password"}), 401

        # Allow either school admin (from registration) or teachers to toggle portal
        # Check if username matches school email (admin) or exists in teachers table
        is_admin = (username == school["email"].strip().lower())
        teacher = conn.execute(
            "SELECT * FROM teachers WHERE school_id = ? AND username = ?",
            (school["id"], username)
        ).fetchone()

        if not is_admin and not teacher:
            return jsonify({"success": False, "message": "User not found"}), 404

        # Get current portal state
        current_state = school["portal_open"]

        # Toggle portal state
        new_state = 0 if current_state == 1 else 1
        conn.execute(
            "UPDATE schools SET portal_open = ? WHERE id = ?",
            (new_state, school["id"])
        )
        conn.commit()

        return jsonify({
            "success": True,
            "portal_open": new_state,
            "message": "Portal opened" if new_state == 1 else "Portal closed"
        })
    except Exception as e:
        logging.error(f"Toggle portal error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/sync_students", methods=["POST"])
@app.route("/api/upload_students", methods=["POST"])
def api_sync_students():
    data = request.json
    school_code = data.get("school_code").strip().lower()
    students_list = data.get("students", [])
    school_details = data.get("school_details", {})

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
        
        # 2. Update school details if provided
        if school_details:
            conn.execute(
                """
                UPDATE schools 
                SET school_address = ?, school_telephone = ?, school_logo = ?
                WHERE id = ?
            """,
                (
                    school_details.get("school_address"),
                    school_details.get("school_telephone"),
                    school_details.get("school_logo"),
                    school_id,
                ),
            )
        
        # 3. Delete all existing students for this school
        conn.execute("DELETE FROM students WHERE school_id = ?", (school_id,))

        # 4. Insert new students
        for s in students_list:
            conn.execute(
                """
                INSERT INTO students (school_id, grade, adm_no, student_name, gender, phone, photo, stream)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    school_id,
                    s["grade"],
                    s["adm_no"],
                    s["name"],
                    s.get("gender"),
                    s.get("phone"),
                    s.get("photo"),
                    s.get("stream", "None"),
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


@app.route("/api/sync_teachers", methods=["POST"])
@app.route("/api/upload_teachers", methods=["POST"])
def api_sync_teachers():
    data = request.json
    school_code = data.get("school_code").strip().lower()
    teachers_list = data.get("teachers", [])

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
        # 2. Delete all existing teacher assignments for this school
        conn.execute("DELETE FROM teacher_assignments WHERE school_id = ?", (school_id,))

        # 3. Insert new teacher assignments
        for t in teachers_list:
            conn.execute(
                """
                INSERT INTO teacher_assignments (school_id, class_name, subject, teacher_name, teacher_code)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    school_id,
                    t["class_name"],
                    t["subject"],
                    t["teacher_name"],
                    t["teacher_code"],
                ),
            )

        conn.commit()
        return jsonify(
            {
                "success": True,
                "message": f"Successfully synced {len(teachers_list)} teacher assignments.",
            }
        )

    except Exception as e:
        logging.error(f"Sync teachers error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/marks/<grade>", methods=["GET", "POST"])
def enter_marks(grade):
    subject = request.args.get("subject")
    if "school_id" not in session:
        return redirect(url_for("teacher_login"))

    conn = get_db()
    # Check if portal is open
    school = conn.execute(
        "SELECT portal_open FROM schools WHERE id = ?", (session["school_id"],)
    ).fetchone()

    if not school or school["portal_open"] == 0:
        conn.close()
        flash("The teachers portal is currently closed. Please contact your administrator.", "danger")
        return redirect(url_for("dashboard"))

    # Verify teacher code for this specific subject
    teacher_code = session.get("teacher_code")
    if not teacher_code:
        conn.close()
        flash("Teacher code not found. Please login again.", "danger")
        return redirect(url_for("teacher_login"))

    # Check if the teacher's code is assigned to this subject for this grade
    teacher_assignment = conn.execute(
        "SELECT * FROM teacher_assignments WHERE school_id = ? AND class_name = ? AND subject = ? AND teacher_code = ?",
        (session["school_id"], grade, subject, teacher_code)
    ).fetchone()

    if not teacher_assignment:
        conn.close()
        flash(f"You are not authorized to enter marks for {subject} in {grade}. Your teacher code does not match.", "danger")
        return redirect(url_for("select_subject", grade=grade))

    # Fetch students for this grade
    students = conn.execute(
        "SELECT * FROM students WHERE school_id = ? AND grade = ? ORDER BY student_name ASC",
        (session["school_id"], grade),
    ).fetchall()

    exam_title = request.args.get("exam_title", EXAM_TITLE_DEFAULT)

    if request.method == "POST":
        now = datetime.utcnow().isoformat()
        
        # Determine grading logic based on grade level
        grade_lower = grade.lower()
        is_jss = any(g in grade_lower for g in ["grade 7", "grade 8", "grade 9"])
        is_primary = any(g in grade_lower for g in ["grade 4", "grade 5", "grade 6"])
        is_lower = any(g in grade_lower for g in ["grade 1", "grade 2", "grade 3"])
        
        for s in students:
            adm = s["adm_no"]
            score = request.form.get(f"score_{adm}")

            # 1. Get existing marks first so we don't overwrite other subjects
            existing = conn.execute(
                "SELECT subject_scores_json FROM marks WHERE school_id=? AND grade=? AND adm_no=? AND exam_title=?",
                (session["school_id"], grade, adm, exam_title),
            ).fetchone()

            scores = json.loads(existing["subject_scores_json"]) if existing else {}

            # 2. Calculate rating and points based on grade level
            rating = ""
            points = 0
            if score and score.strip():
                try:
                    score_int = int(score)
                    if is_jss:
                        rating, points = get_grade_7_8_rating(score_int)
                    elif is_primary or is_lower:
                        rating = get_grade_4_6_rating(score_int)
                        # For primary, map rating to points using the same scale
                        level_points = {"EE1": 8, "EE2": 7, "ME1": 6, "ME2": 5, "AE1": 4, "AE2": 3, "BE1": 2, "BE2": 1}
                        points = level_points.get(rating, 0)
                    else:
                        # For early years (playgroup, pp1, pp2), use primary logic as fallback
                        rating = get_grade_4_6_rating(score_int)
                        level_points = {"EE1": 8, "EE2": 7, "ME1": 6, "ME2": 5, "AE1": 4, "AE2": 3, "BE1": 2, "BE2": 1}
                        points = level_points.get(rating, 0)
                except ValueError:
                    rating = ""
                    points = 0

            # 3. Update the specific subject with score, rating, and points
            scores[subject] = {"score": score, "rating": rating, "points": points}

            # 4. Calculate total points and average level across all subjects
            total_points = 0
            subject_count = 0
            for subj, data in scores.items():
                if data.get("points"):
                    total_points += int(data["points"])
                    subject_count += 1

            # Calculate average level
            if is_jss:
                # JSS uses points sum for final level
                avg_level = calculate_final_level(total_points, is_primary=False)
            else:
                # Primary uses raw score sum for final level
                total_score = 0
                for subj, data in scores.items():
                    if data.get("score"):
                        try:
                            total_score += int(data["score"])
                        except ValueError:
                            pass
                avg_level = calculate_final_level(total_score, is_primary=True)

            conn.execute(
                """
                INSERT INTO marks (school_id, grade, adm_no, student_name, exam_title, subject_scores_json, total_points, average_level, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(school_id, grade, adm_no, exam_title) DO UPDATE SET
                subject_scores_json = excluded.subject_scores_json,
                total_points = excluded.total_points,
                average_level = excluded.average_level,
                updated_at = excluded.updated_at
            """,
                (
                    session["school_id"],
                    grade,
                    adm,
                    s["student_name"],
                    exam_title,
                    json.dumps(scores),
                    str(total_points),
                    avg_level,
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
        return redirect(url_for("teacher_login"))

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
    
    # Determine grading logic based on grade level
    grade_lower = gr.lower() if gr else ""
    is_jss = any(g in grade_lower for g in ["grade 7", "grade 8", "grade 9"])
    is_primary = any(g in grade_lower for g in ["grade 4", "grade 5", "grade 6"])
    is_lower = any(g in grade_lower for g in ["grade 1", "grade 2", "grade 3"])
    
    # 3. Package them up with calculated rating/points if missing
    marks_list = []
    for r in rows:
        scores = json.loads(r["subject_scores_json"])
        print(f"DEBUG API: Processing record for {r['student_name']}, original scores: {scores}")
        
        # Calculate missing rating and points for each subject
        for subject, data in scores.items():
            # Handle old format where data might be just a string score
            if isinstance(data, str):
                score = data
                rating = ""
                points = 0
                if score and str(score).strip():
                    try:
                        score_int = int(score)
                        if is_jss:
                            rating, points = get_grade_7_8_rating(score_int)
                        elif is_primary or is_lower:
                            rating = get_grade_4_6_rating(score_int)
                            level_points = {"EE1": 8, "EE2": 7, "ME1": 6, "ME2": 5, "AE1": 4, "AE2": 3, "BE1": 2, "BE2": 1}
                            points = level_points.get(rating, 0)
                        else:
                            rating = get_grade_4_6_rating(score_int)
                            level_points = {"EE1": 8, "EE2": 7, "ME1": 6, "ME2": 5, "AE1": 4, "AE2": 3, "BE1": 2, "BE2": 1}
                            points = level_points.get(rating, 0)
                        print(f"DEBUG API: Converted old format {subject}: score={score_int} -> rating={rating}, points={points}")
                    except ValueError:
                        rating = ""
                        points = 0
                
                # Convert to new dict format
                scores[subject] = {"score": score, "rating": rating, "points": points}
            elif isinstance(data, dict):
                # If rating or points are missing, calculate them
                if "rating" not in data or "points" not in data or not data.get("rating"):
                    score = data.get("score", "")
                    rating = ""
                    points = 0
                    if score and str(score).strip():
                        try:
                            score_int = int(score)
                            if is_jss:
                                rating, points = get_grade_7_8_rating(score_int)
                            elif is_primary or is_lower:
                                rating = get_grade_4_6_rating(score_int)
                                level_points = {"EE1": 8, "EE2": 7, "ME1": 6, "ME2": 5, "AE1": 4, "AE2": 3, "BE1": 2, "BE2": 1}
                                points = level_points.get(rating, 0)
                            else:
                                rating = get_grade_4_6_rating(score_int)
                                level_points = {"EE1": 8, "EE2": 7, "ME1": 6, "ME2": 5, "AE1": 4, "AE2": 3, "BE1": 2, "BE2": 1}
                                points = level_points.get(rating, 0)
                            print(f"DEBUG API: Calculated missing {subject}: score={score_int} -> rating={rating}, points={points}")
                        except ValueError:
                            rating = ""
                            points = 0
                    
                    # Update the data with calculated values
                    data["rating"] = rating
                    data["points"] = points
                    scores[subject] = data
        
        # Calculate total_points and average_level if missing
        # Junior (JSS) uses points for total, all other grades use scores
        if is_jss:
            total_points = 0
            for subject, data in scores.items():
                if isinstance(data, dict) and data.get("points"):
                    try:
                        total_points += int(data["points"])
                    except ValueError:
                        pass
            print(f"DEBUG API: Calculated total_points (from points)={total_points} for JSS")
        else:
            total_points = 0
            for subject, data in scores.items():
                if isinstance(data, dict) and data.get("score"):
                    try:
                        total_points += int(data["score"])
                    except ValueError:
                        pass
            print(f"DEBUG API: Calculated total_points (from scores)={total_points} for non-JSS")
        
        # Calculate average level
        if is_jss:
            avg_level = calculate_final_level(total_points, is_primary=False)
        else:
            avg_level = calculate_final_level(total_points, is_primary=True)
            print(f"DEBUG API: Calculated avg_level={avg_level} from total_points={total_points}")
        
        # Use calculated values if database values are missing or empty
        db_total_points = r["total_points"] if r["total_points"] is not None else "0"
        db_avg_level = r["average_level"] if r["average_level"] is not None else ""
        
        print(f"DEBUG API: DB values - total_points={db_total_points}, avg_level={db_avg_level}")
        print(f"DEBUG API: Calculated values - total_points={total_points}, avg_level={avg_level}")
        
        # Always use calculated values to ensure accuracy
        db_total_points = str(total_points)
        db_avg_level = avg_level
        print(f"DEBUG API: Using calculated values - total_points={db_total_points}, avg_level={db_avg_level}")
        
        marks_list.append(
            {
                "adm_no": r["adm_no"],
                "student_name": r["student_name"],
                "grade": r["grade"],
                "exam_title": r["exam_title"],
                "scores": scores,
                "total_points": db_total_points,
                "average_level": db_avg_level,
            }
        )

    # Return with the key 'marks'
    return jsonify({"success": True, "marks": marks_list})


@app.route("/api/consume_marks", methods=["POST"])
def api_consume_marks():
    """Delete marks from cloud after they've been fetched (consume operation)"""
    data = request.json
    sc = data.get("school_code", "").strip().lower()
    gr = data.get("grade")

    conn = get_db()
    try:
        # 1. Find school
        school = conn.execute(
            "SELECT id FROM schools WHERE school_code=?", (sc,)
        ).fetchone()

        if not school:
            return jsonify({"success": False, "message": "School not found"}), 404

        # 2. Delete marks for that grade
        cursor = conn.execute(
            "DELETE FROM marks WHERE school_id = ? AND grade = ?", (school["id"], gr)
        )
        deleted_count = cursor.rowcount
        conn.commit()

        print(f"DEBUG: Consumed {deleted_count} marks from cloud for school {sc} grade {gr}")
        return jsonify({
            "success": True,
            "message": f"Consumed {deleted_count} marks from cloud"
        })

    except Exception as e:
        logging.error(f"Consume marks error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/students/<grade>")
def manage_students(grade):
    if "school_id" not in session:
        return redirect(url_for("teacher_login"))

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


@app.route("/api/save_student_report", methods=["POST"])
def api_save_student_report():
    """Save a student report to the cloud database"""
    data = request.json
    school_code = data.get("school_code", "").strip().lower()
    report = data.get("report", {})

    logging.info(f"Received student report for: {report.get('student_name')}, keys: {list(report.keys())}")
    if 'exam_title' in report:
        logging.info(f"Report contains exam_title: {report['exam_title']}")
    else:
        logging.warning("Report does NOT contain exam_title!")

    if not school_code or not report:
        return jsonify({"success": False, "message": "Missing required data"}), 400

    conn = get_db()
    try:
        # Verify school
        school = conn.execute(
            "SELECT id, school_name FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()
        if not school:
            return jsonify({"success": False, "message": "School not found"}), 404

        # Save or update the student report
        import json
        report_json = json.dumps(report)
        generated_date = report.get("generated_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        logging.info(f"Saving report - student_name: {report.get('student_name')}, adm_no: {report.get('adm_no')} (type: {type(report.get('adm_no'))}), grade: {report.get('grade')}, school: {school['school_name']}")

        conn.execute(
            """
            INSERT OR REPLACE INTO student_reports
            (student_name, adm_no, grade, school_name, report_data, generated_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                report.get("student_name", ""),
                report.get("adm_no", ""),
                report.get("grade", ""),
                school["school_name"],
                report_json,
                generated_date
            )
        )
        conn.commit()
        
        # Send FCM notification for report
        try:
            from fcm_service import get_fcm_service
            fcm_service = get_fcm_service()
            
            if fcm_service.is_available():
                # Get student ID for FCM token lookup
                student_cursor = conn.execute(
                    "SELECT id FROM students WHERE student_name = ? AND adm_no = ? AND grade = ?",
                    (report.get("student_name"), report.get("adm_no"), report.get("grade"))
                )
                student_row = student_cursor.fetchone()
                
                if student_row:
                    student_id = student_row[0]
                    # Get FCM token for this student
                    token_cursor = conn.execute(
                        "SELECT token FROM fcm_tokens WHERE student_id = ?",
                        (student_id,)
                    )
                    token_row = token_cursor.fetchone()
                    
                    if token_row:
                        token = token_row[0]
                        exam_title = report.get("exam_title", "New Report")
                        result = fcm_service.send_notification(
                            token=token,
                            title=f"New Report: {exam_title}",
                            body=f"A new report has been published for {report.get('student_name')}",
                            data={
                                "type": "report",
                                "student_name": report.get("student_name"),
                                "adm_no": report.get("adm_no")
                            }
                        )
                        logging.info(f"FCM notification sent for report: {result}")
                    else:
                        logging.info("No FCM token found for student")
                else:
                    logging.info("Student not found in database")
            else:
                logging.info("FCM service not available, skipping report notification")
        except Exception as e:
            logging.error(f"Error sending FCM notification for report: {e}")

        return jsonify({"success": True, "message": "Report saved successfully"})
    except Exception as e:
        logging.error(f"Save student report error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/register_fcm_token", methods=["POST"])
def api_register_fcm_token():
    """Register an FCM token for a student"""
    logging.info("=== FCM Token Registration Request ===")
    try:
        data = request.json
        student_id = data.get("student_id")
        token = data.get("token")
        device_info = data.get("device_info", "")
        
        logging.info(f"Received FCM token registration - student_id: {student_id}, token: {token[:20]}... if token else None, device: {device_info[:50]}...")
        
        if not student_id or not token:
            logging.warning("FCM token registration failed: Missing student_id or token")
            return jsonify({"success": False, "message": "Missing student_id or token"}), 400
        
        conn = get_db()
        try:
            # Insert or update the token
            conn.execute("""
                INSERT OR REPLACE INTO fcm_tokens (student_id, token, device_info, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (student_id, token, device_info))
            
            conn.commit()
            logging.info(f"✓ FCM token registered successfully for student_id={student_id}")
            return jsonify({"success": True, "message": "Token registered successfully"})
            
        except Exception as e:
            logging.error(f"Error registering FCM token in database: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logging.error(f"FCM token registration error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/save_newsletter", methods=["POST"])
def api_save_newsletter():
    """Save a newsletter to the cloud database"""
    data = request.json
    school_code = data.get("school_code", "").strip().lower()
    username = data.get("username", "")
    password = data.get("password", "")
    newsletter_data = data.get("newsletter", {})

    logging.info(f"Received newsletter: {newsletter_data.get('subject')}, target: {newsletter_data.get('target_type')}")

    if not school_code or not newsletter_data:
        return jsonify({"success": False, "message": "Missing required data"}), 400

    conn = get_db()
    try:
        # Verify school and authenticate user
        school = conn.execute(
            "SELECT id, school_name FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()
        if not school:
            return jsonify({"success": False, "message": "School not found"}), 404

        # Create tables if they don't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS newsletters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                target_type TEXT,
                class_context TEXT,
                recipient_role TEXT,
                attachment_path TEXT,
                send_email INTEGER DEFAULT 0,
                send_sms INTEGER DEFAULT 0,
                is_draft INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP
            )
        """)
        
        # Migrate old schema if needed (add new columns if they don't exist)
        try:
            # Check if table has old columns (title, content) and migrate to new columns (subject, body)
            cursor = conn.execute("PRAGMA table_info(newsletters)")
            columns = {row[1] for row in cursor.fetchall()}
            
            if 'title' in columns and 'subject' not in columns:
                logging.info("Migrating newsletters table from old schema to new schema")
                conn.execute("ALTER TABLE newsletters ADD COLUMN subject TEXT")
                conn.execute("ALTER TABLE newsletters ADD COLUMN body TEXT")
                conn.execute("ALTER TABLE newsletters ADD COLUMN target_type TEXT")
                conn.execute("ALTER TABLE newsletters ADD COLUMN class_context TEXT")
                conn.execute("ALTER TABLE newsletters ADD COLUMN recipient_role TEXT")
                conn.execute("ALTER TABLE newsletters ADD COLUMN send_email INTEGER DEFAULT 0")
                conn.execute("ALTER TABLE newsletters ADD COLUMN send_sms INTEGER DEFAULT 0")
                conn.execute("ALTER TABLE newsletters ADD COLUMN is_draft INTEGER DEFAULT 1")
                conn.execute("ALTER TABLE newsletters ADD COLUMN sent_at TIMESTAMP")
                
                # Copy data from old columns to new columns
                conn.execute("UPDATE newsletters SET subject = title WHERE subject IS NULL")
                conn.execute("UPDATE newsletters SET body = content WHERE body IS NULL")
                
                conn.commit()
                logging.info("Newsletter table migration completed")
        except Exception as e:
            logging.error(f"Error migrating newsletters table: {e}")
            # Continue anyway - table might already have correct schema
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portal_announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                newsletter_id INTEGER,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                target_type TEXT,
                class_context TEXT NOT NULL,
                recipient_role TEXT,
                attachment_path TEXT,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(newsletter_id) REFERENCES newsletters(id)
            )
        """)
        
        # Migrate portal_announcements table if needed
        try:
            cursor = conn.execute("PRAGMA table_info(portal_announcements)")
            columns = {row[1] for row in cursor.fetchall()}
            
            if 'title' in columns and 'subject' not in columns:
                logging.info("Migrating portal_announcements table from old schema to new schema")
                conn.execute("ALTER TABLE portal_announcements ADD COLUMN subject TEXT")
                conn.execute("ALTER TABLE portal_announcements ADD COLUMN body TEXT")
                conn.execute("ALTER TABLE portal_announcements ADD COLUMN target_type TEXT")
                conn.execute("ALTER TABLE portal_announcements ADD COLUMN recipient_role TEXT")
                conn.execute("ALTER TABLE portal_announcements ADD COLUMN attachment_path TEXT")
                
                # Copy data from old columns to new columns
                conn.execute("UPDATE portal_announcements SET subject = title WHERE subject IS NULL")
                conn.execute("UPDATE portal_announcements SET body = content WHERE body IS NULL")
                
                conn.commit()
                logging.info("Portal_announcements table migration completed")
            elif 'attachment_path' not in columns:
                # Add attachment_path if missing but other columns exist
                logging.info("Adding attachment_path column to portal_announcements table")
                conn.execute("ALTER TABLE portal_announcements ADD COLUMN attachment_path TEXT")
                conn.commit()
        except Exception as e:
            logging.error(f"Error migrating portal_announcements table: {e}")
        
        conn.execute("""
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

        # Insert into newsletters table (handle both old and new schemas)
        cursor = conn.execute("PRAGMA table_info(newsletters)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'title' in columns:
            # Old schema - use title and content columns
            cursor = conn.execute("""
                INSERT INTO newsletters (
                    title, content, target_type, class_context, recipient_role,
                    attachment_path, send_email, send_sms, is_draft, sent_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                newsletter_data.get("subject"),
                newsletter_data.get("body"),
                newsletter_data.get("target_type"),
                newsletter_data.get("class_context"),
                newsletter_data.get("recipient_role"),
                newsletter_data.get("attachment_path"),
                newsletter_data.get("send_email", 0),
                newsletter_data.get("send_sms", 0),
                0,  # is_draft = 0 (published)
                "CURRENT_TIMESTAMP"
            ))
        else:
            # New schema - use subject and body columns
            cursor = conn.execute("""
                INSERT INTO newsletters (
                    subject, body, target_type, class_context, recipient_role,
                    attachment_path, send_email, send_sms, is_draft, sent_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                newsletter_data.get("subject"),
                newsletter_data.get("body"),
                newsletter_data.get("target_type"),
                newsletter_data.get("class_context"),
                newsletter_data.get("recipient_role"),
                newsletter_data.get("attachment_path"),
                newsletter_data.get("send_email", 0),
                newsletter_data.get("send_sms", 0),
                0,  # is_draft = 0 (published)
                "CURRENT_TIMESTAMP"
            ))
        
        newsletter_id = cursor.lastrowid
        
        # Insert into portal_announcements table (handle both old and new schemas)
        cursor = conn.execute("PRAGMA table_info(portal_announcements)")
        columns_info = cursor.fetchall()
        columns = {row[1]: row[2] for row in columns_info}  # column name: type
        
        # Log column order for debugging
        logging.info(f"Portal announcements columns: {[row[1] for row in columns_info]}")
        
        if 'title' in columns:
            # Old schema - use title and content columns
            # Check if it's the really old schema with published_at in position 4
            if len(columns_info) <= 5:
                # Very old schema: id, newsletter_id, title, content, published_at
                # class_context might not exist or be in wrong position
                logging.info("Using very old schema INSERT")
                cursor = conn.execute("""
                    INSERT INTO portal_announcements (
                        newsletter_id, title, content, published_at
                    ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    newsletter_id,
                    newsletter_data.get("subject"),
                    newsletter_data.get("body")
                ))
                # Try to add class_context if column exists
                if 'class_context' in columns:
                    announcement_id = cursor.lastrowid
                    conn.execute("UPDATE portal_announcements SET class_context = ? WHERE id = ?",
                               (newsletter_data.get("class_context"), announcement_id))
            elif 'attachment_path' in columns and 'target_type' in columns:
                # Migrated old schema with new columns - use positional INSERT to avoid column name issues
                logging.info("Using migrated old schema INSERT with positional values")
                # Column order: id, newsletter_id, title, content, class_context, published_at, subject, body, target_type, recipient_role, attachment_path
                cursor = conn.execute("""
                    INSERT INTO portal_announcements 
                    (newsletter_id, title, content, class_context, published_at, subject, body, target_type, recipient_role, attachment_path)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
                """, (
                    newsletter_id,
                    newsletter_data.get("subject"),
                    newsletter_data.get("body"),
                    newsletter_data.get("class_context"),
                    newsletter_data.get("subject"),  # subject (new column)
                    newsletter_data.get("body"),     # body (new column)
                    newsletter_data.get("target_type"),
                    newsletter_data.get("recipient_role"),
                    newsletter_data.get("attachment_path")
                ))
            else:
                # Pure old schema without new columns
                logging.info("Using pure old schema INSERT")
                cursor = conn.execute("""
                    INSERT INTO portal_announcements (
                        newsletter_id, title, content, class_context, published_at
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    newsletter_id,
                    newsletter_data.get("subject"),
                    newsletter_data.get("body"),
                    newsletter_data.get("class_context")
                ))
        else:
            # New schema - use subject and body columns
            logging.info("Using new schema INSERT")
            if 'attachment_path' in columns:
                cursor = conn.execute("""
                    INSERT INTO portal_announcements (
                        newsletter_id, subject, body, target_type, 
                        class_context, recipient_role, attachment_path, published_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    newsletter_id,
                    newsletter_data.get("subject"),
                    newsletter_data.get("body"),
                    newsletter_data.get("target_type"),
                    newsletter_data.get("class_context"),
                    newsletter_data.get("recipient_role"),
                    newsletter_data.get("attachment_path")
                ))
            else:
                cursor = conn.execute("""
                    INSERT INTO portal_announcements (
                        newsletter_id, subject, body, target_type, 
                        class_context, recipient_role, published_at
                    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    newsletter_id,
                    newsletter_data.get("subject"),
                    newsletter_data.get("body"),
                    newsletter_data.get("target_type"),
                    newsletter_data.get("class_context"),
                    newsletter_data.get("recipient_role")
                ))
        
        announcement_id = cursor.lastrowid
        
        # Create notification entries based on target type
        target_type = newsletter_data.get("target_type")
        class_context = newsletter_data.get("class_context")
        recipient_role = newsletter_data.get("recipient_role")
        
        student_ids = []
        if target_type == "Individual Student":
            # Get specific student - use student_name for cloud database
            cursor = conn.execute(
                "SELECT id FROM students WHERE student_name = ? AND grade = ?",
                (recipient_role, class_context)
            )
            student_row = cursor.fetchone()
            if student_row:
                student_ids = [student_row[0]]
        elif target_type == "By Stream":
            # Get students in specific stream
            cursor = conn.execute(
                "SELECT id FROM students WHERE grade = ? AND stream = ?",
                (class_context, recipient_role)
            )
            student_ids = [row[0] for row in cursor.fetchall()]
        elif class_context == "All Classes" or target_type == "All School":
            # Get all students
            cursor = conn.execute("SELECT id FROM students")
            student_ids = [row[0] for row in cursor.fetchall()]
        else:
            # Get students in specific class
            cursor = conn.execute("SELECT id FROM students WHERE grade = ?", (class_context,))
            student_ids = [row[0] for row in cursor.fetchall()]
        
        # Create notification entries
        for student_id in student_ids:
            conn.execute("""
                INSERT OR IGNORE INTO parent_view_status (student_id, content_type, content_id, has_viewed)
                VALUES (?, ?, ?, 0)
            """, (student_id, 'newsletter', announcement_id))
        
        conn.commit()
        
        # Keep only the 3 latest newsletters (delete old ones)
        try:
            cursor = conn.execute("""
                DELETE FROM portal_announcements 
                WHERE id NOT IN (
                    SELECT id FROM portal_announcements 
                    ORDER BY published_at DESC 
                    LIMIT 3
                )
            """)
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                logging.info(f"Deleted {deleted_count} old newsletters, keeping only 3 latest")
            conn.commit()
        except Exception as e:
            logging.error(f"Error deleting old newsletters: {e}")
        
        # Send FCM notifications
        try:
            from fcm_service import get_fcm_service
            fcm_service = get_fcm_service()
            
            if fcm_service.is_available():
                # Get FCM tokens for target students
                tokens = []
                for student_id in student_ids:
                    cursor = conn.execute(
                        "SELECT token FROM fcm_tokens WHERE student_id = ?",
                        (student_id,)
                    )
                    token_row = cursor.fetchone()
                    if token_row:
                        tokens.append(token_row[0])
                
                if tokens:
                    # Send multicast notification
                    result = fcm_service.send_multicast_notification(
                        tokens=tokens,
                        title=f"New Newsletter: {newsletter_data.get('subject')}",
                        body="A new newsletter has been published. Check your portal.",
                        data={
                            "type": "newsletter",
                            "announcement_id": str(announcement_id),
                            "subject": newsletter_data.get('subject')
                        }
                    )
                    logging.info(f"FCM notifications sent: {result}")
                else:
                    logging.info("No FCM tokens found for target students")
            else:
                logging.info("FCM service not available, skipping push notifications")
                
        except Exception as e:
            logging.error(f"Error sending FCM notifications: {e}")
        
        logging.info(f"Newsletter synced to cloud: {newsletter_data.get('subject')}, {len(student_ids)} notifications created")
        return jsonify({"success": True, "message": f"Newsletter saved successfully, {len(student_ids)} notifications created"})
        
    except Exception as e:
        logging.error(f"Save newsletter error: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/save_class_reports", methods=["POST"])
def api_save_class_reports():
    """Save multiple reports for a class"""
    data = request.json
    school_code = data.get("school_code", "").strip().lower()
    class_name = data.get("class_name", "")
    reports = data.get("reports", [])

    if not school_code or not reports:
        return jsonify({"success": False, "message": "Missing required data"}), 400

    conn = get_db()
    try:
        # Verify school
        school = conn.execute(
            "SELECT id, school_name FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()
        if not school:
            return jsonify({"success": False, "message": "School not found"}), 404

        # Save all reports
        import json
        saved_count = 0
        for report in reports:
            report_json = json.dumps(report)
            generated_date = report.get("generated_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            conn.execute(
                """
                INSERT OR REPLACE INTO student_reports
                (student_name, adm_no, grade, school_name, report_data, generated_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report.get("student_name", ""),
                    report.get("adm_no", ""),
                    report.get("grade", ""),
                    school["school_name"],
                    report_json,
                    generated_date
                )
            )
            saved_count += 1
        conn.commit()

        return jsonify({"success": True, "message": f"Saved {saved_count} reports successfully"})
    except Exception as e:
        logging.error(f"Save class reports error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/clear_student_reports", methods=["POST"])
def api_clear_student_reports():
    """Clear all student reports from the database to force fallback usage"""
    data = request.json
    school_code = data.get("school_code", "").strip()
    
    if not school_code:
        return jsonify({"success": False, "message": "Missing school_code"}), 400
    
    conn = get_db()
    try:
        # Verify school
        school = conn.execute(
            "SELECT id FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()
        if not school:
            return jsonify({"success": False, "message": "School not found"}), 404
        
        # Delete all student reports
        conn.execute("DELETE FROM student_reports")
        conn.commit()
        
        logging.info("Cleared all student reports from database")
        return jsonify({"success": True, "message": "All student reports cleared"})
    except Exception as e:
        logging.error(f"Clear student reports error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/fetch_parent_report", methods=["POST"])
def api_fetch_parent_report():
    """Fetch a student's report for parent view"""
    data = request.json
    student_name = data.get("student_name", "").strip()
    school_name = data.get("school_name", "").strip()
    adm_no = data.get("adm_no", "").strip()

    if not student_name or not school_name or not adm_no:
        return jsonify({"success": False, "message": "Missing required data"}), 400

    conn = get_db()
    try:
        # Find the report
        report = conn.execute(
            """
            SELECT report_data, generated_date FROM student_reports
            WHERE student_name = ? AND school_name = ? AND adm_no = ?
            ORDER BY generated_date DESC LIMIT 1
            """,
            (student_name, school_name, adm_no)
        ).fetchone()

        if not report:
            return jsonify({"success": False, "message": "Report not found"}), 404

        import json
        report_data = json.loads(report["report_data"])

        return jsonify({
            "success": True,
            "report": report_data,
            "generated_date": report["generated_date"]
        })
    except Exception as e:
        logging.error(f"Fetch parent report error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/parent/login", methods=["GET", "POST"])
def parent_login():
    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        school_name = request.form.get("school_name", "").strip()
        adm_no = request.form.get("adm_no", "").strip()

        if not student_name or not school_name or not adm_no:
            flash("Please fill in all fields", "error")
            return render_template("cloud_parent_login.html")

        # Verify student exists
        conn = get_db()
        try:
            student = conn.execute(
                """
                SELECT s.id, s.school_id, s.grade, sc.school_name
                FROM students s
                JOIN schools sc ON s.school_id = sc.id
                WHERE s.student_name = ? AND sc.school_name = ? AND s.adm_no = ?
                """,
                (student_name, school_name, adm_no)
            ).fetchone()

            if student:
                session["parent_student_id"] = student["id"]
                session["parent_student_name"] = student_name
                session["parent_school_name"] = school_name
                session["parent_adm_no"] = adm_no
                session["parent_grade"] = student["grade"]
                return redirect(url_for("parent_dashboard"))
            else:
                flash("Student not found. Please check your details.", "error")
        except Exception as e:
            logging.error(f"Parent login error: {e}")
            flash("An error occurred. Please try again.", "error")
        finally:
            conn.close()

    return render_template("cloud_parent_login.html")


@app.route("/parent/dashboard")
def parent_dashboard():
    logging.info(f"Parent dashboard accessed, session keys: {list(session.keys())}")
    if "parent_student_id" not in session:
        logging.warning("Parent dashboard: No parent_student_id in session")
        return redirect(url_for("parent_login"))

    # Check for unread notifications
    conn = get_db()
    try:
        student_id = session.get("parent_student_id")
        
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
            school_name=session.get("parent_school_name"),
            student_name=session.get("parent_student_name"),
            student_grade=session.get("parent_grade"),
            student_adm_no=session.get("parent_adm_no"),
            unread_newsletters=unread_newsletters,
            unread_reports=unread_reports
        )
    finally:
        conn.close()


@app.route("/parent/report")
def parent_report():
    logging.info(f"Parent report accessed, session keys: {list(session.keys())}")
    if "parent_student_id" not in session:
        logging.warning("Parent report: No parent_student_id in session")
        return redirect(url_for("parent_login"))

    conn = get_db()
    try:
        # Fetch the student's report
        logging.info(f"Fetching report for student: {session.get('parent_student_name')}, school: {session.get('parent_school_name')}, adm_no: {session.get('parent_adm_no')} (type: {type(session.get('parent_adm_no'))})")
        
        report = conn.execute(
            """
            SELECT report_data, generated_date FROM student_reports
            WHERE student_name = ? AND school_name = ? AND adm_no = ?
            ORDER BY generated_date DESC LIMIT 1
            """,
            (session["parent_student_name"], session["parent_school_name"], session["parent_adm_no"])
        ).fetchone()
        logging.info(f"Report fetch result: {report is not None}")
        if report:
            logging.info(f"Report found for {session['parent_student_name']}, generated_date: {report['generated_date']}")
        else:
            logging.warning(f"Report NOT found for {session['parent_student_name']} with adm_no: {session['parent_adm_no']}")

        import json
        if report:
            logging.info("Report found, parsing JSON")
            report_data = json.loads(report["report_data"])
            # Generate analytics data
            logging.info("Generating analytics")
            report_data = generate_analytics(report_data, conn, session["parent_grade"])
        else:
            logging.info("No report found for student, checking available tables for fallback")
            # Fallback: fetch data directly from marksheet table
            grade = session["parent_grade"]
            table_mapping = {
                'playgroup': 'playgroup_marks',
                'pp1': 'pp1_marks',
                'pp2': 'pp2_marks',
                'Grade 1': 'lower_marks',
                'Grade 2': 'lower_marks',
                'Grade 3': 'lower_marks',
                'Grade 4': 'primary_marks',
                'Grade 7': 'marks',
                'Grade 8': 'marks',
                'Grade 9': 'marks',
            }
            table = table_mapping.get(grade)
            if table:
                # Check if table exists before querying
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                table_exists = cursor.fetchone()
                # Log available tables for debugging
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                all_tables = [row[0] for row in cursor.fetchall()]
                logging.info(f"Fallback: Available tables in database: {all_tables}")
                logging.info(f"Fallback: Looking for table '{table}' for grade '{grade}'")
                if table_exists:
                    conn.execute(f'SELECT * FROM {table} WHERE adm_no = ?', (session["parent_adm_no"],))
                    columns = [desc[0] for desc in conn.description]
                    row = conn.fetchone()
                    if row:
                        current_marks = dict(zip(columns, row))
                        # Use average_points for junior, average_level for others
                        if grade in ['Grade 7', 'Grade 8', 'Grade 9']:
                            if 'average_points' in current_marks:
                                if current_marks['average_points']:
                                    current_marks['average_level'] = current_marks['average_points']
                                else:
                                    current_marks['average_level'] = ''
                        report_data = {
                            'current_marks': current_marks,
                        'exam_title': current_exam_title if 'current_exam_title' in locals() else 'Current Exam',
                        'previous_exams': []
                    }
                    # Log subject-related keys for debugging
                    subject_keys = [k for k in current_marks.keys() if 'scie' in k.lower() or 'int' in k.lower()]
                    logging.info(f"Fallback: Retrieved data from {table} with subject keys: {subject_keys}")
                    logging.info(f"Fallback: All keys: {list(current_marks.keys())[:15]}")
                    # Log actual values for int_scie columns
                    if 'int_scie_s' in current_marks:
                        logging.info(f"Fallback: int_scie_s = {current_marks['int_scie_s']}")
                    if 'int_scie_r' in current_marks:
                        logging.info(f"Fallback: int_scie_r = {current_marks['int_scie_r']}")
                    if 'int_scie_p' in current_marks:
                        logging.info(f"Fallback: int_scie_p = {current_marks['int_scie_p']}")
                    if 'average_points' in current_marks:
                        logging.info(f"Fallback: average_points = {current_marks['average_points']}")
                    if 'average_level' in current_marks:
                        logging.info(f"Fallback: average_level = {current_marks['average_level']}")
                else:
                    logging.warning(f"Fallback: Table '{table}' does not exist in cloud database")
                    report_data = None
            else:
                logging.warning(f"Fallback: No table mapping found for grade '{grade}'")
                report_data = None

        # Determine current exam title from report data or use default
        if report_data and 'exam_title' in report_data and report_data['exam_title']:
            current_exam_title = report_data['exam_title']
            logging.info(f"Using exam_title from report data: {current_exam_title}")
        else:
            # Try to get exam title from school config
            school_config_query = conn.execute(
                "SELECT school_address, school_telephone, school_logo FROM schools WHERE school_name = ?",
                (session["parent_school_name"],)
            ).fetchone()
            
            grade = session["parent_grade"]
            grade_lower = grade.lower() if grade else ""
            current_exam_title = "Current Exam"
            
            if grade_lower in ["playgroup", "pp1", "pp2"]:
                current_exam_title = "TERM ASSESSMENT"
            elif grade_lower in ["grade 1", "grade 2", "grade 3", "grade 4", "grade 5", "grade 6"]:
                current_exam_title = "PRIMARY EXAM"
            elif grade_lower in ["grade 7", "grade 8", "grade 9"]:
                current_exam_title = "JSS ASSESSMENT"
            
            logging.info(f"Using fallback exam_title for grade {grade}: {current_exam_title}")

        # Use previous exams from report data if available
        if report_data and 'previous_exams' in report_data:
            previous_exams_list = report_data['previous_exams']
            logging.info(f"Using {len(previous_exams_list)} previous exams from report data")

            # Database already returns exams in DESC order (newest first), so no reversal needed
            # previous_exams_list = list(reversed(previous_exams_list))

            # Convert to format expected by template
            previous_exams = []
            previous_exam_marks = {}
            for prev_exam in previous_exams_list:
                previous_exams.append({
                    'exam_title': prev_exam['exam_name'],
                    'exam_date': prev_exam['exam_date'],
                    'average_level': prev_exam.get('average_level')
                })
                marks = prev_exam['marks']
                # Parse marks if it's a JSON string
                if isinstance(marks, str):
                    try:
                        marks = json.loads(marks)
                        logging.info(f"Parsed marks from JSON string for exam {prev_exam['exam_name']}")
                    except:
                        logging.error(f"Failed to parse marks as JSON for exam {prev_exam['exam_name']}")
                        marks = {}
                previous_exam_marks[prev_exam['exam_name']] = marks
                logging.info(f"Previous exam: {prev_exam['exam_name']}, marks type: {type(marks)}, is dict: {isinstance(marks, dict)}, is list: {isinstance(marks, list)}")
                if isinstance(marks, dict):
                    logging.info(f"  marks keys: {list(marks.keys())[:5]}")
                    logging.info(f"  marks sample: {list(marks.items())[:2]}")
                elif isinstance(marks, list):
                    logging.info(f"  marks length: {len(marks)}")
                    logging.info(f"  marks sample: {marks[:5]}")
            logging.info(f"previous_exam_marks keys: {list(previous_exam_marks.keys())}")
        else:
            # Fallback to querying marks table
            logging.info("No previous exams in report data, querying marks table")
            previous_exams = []
            previous_exam_marks = {}

        # Fetch school details from database
        school = conn.execute(
            """
            SELECT school_address, school_telephone, school_logo, school_administrator, school_signature
            FROM schools
            WHERE school_name = ?
            """,
            (session["parent_school_name"],)
        ).fetchone()

        school_address = school["school_address"] if school else None
        school_telephone = school["school_telephone"] if school else None
        school_logo = school["school_logo"] if school else None
        school_administrator = school["school_administrator"] if school else "School Administrator"
        school_signature = school["school_signature"] if school else ""

        logging.info(f"School details - administrator: {school_administrator}, signature: {'present' if school_signature else 'missing'}")

        # Fetch student photo and stream from database
        student = conn.execute(
            """
            SELECT photo, stream FROM students
            WHERE student_name = ? AND adm_no = ?
            """,
            (session["parent_student_name"], session["parent_adm_no"])
        ).fetchone()

        student_photo = student["photo"] if student and student["photo"] else None
        student_stream = student["stream"] if student and student["stream"] else "None"

        # Fetch school_id from database using school_name
        school = conn.execute(
            "SELECT id FROM schools WHERE school_name = ?",
            (session["parent_school_name"],)
        ).fetchone()
        
        school_id = school["id"] if school else None

        # Fetch teacher assignments for this grade
        teacher_assignments = conn.execute(
            """
            SELECT subject, teacher_name FROM teacher_assignments
            WHERE school_id = ? AND class_name = ?
            """,
            (school_id, session["parent_grade"])
        ).fetchall()

        # Create a dictionary mapping subject to teacher name
        teacher_map = {row["subject"]: row["teacher_name"] for row in teacher_assignments}

        logging.info("Rendering dashboard template")
        return render_template(
            "cloud_parent_dashboard.html",
            student_name=session["parent_student_name"],
            adm_no=session["parent_adm_no"],
            grade=session["parent_grade"],
            school_name=session["parent_school_name"],
            school_address=school_address,
            school_telephone=school_telephone,
            school_logo=school_logo,
            school_administrator=school_administrator,
            school_signature=school_signature,
            student_photo=student_photo,
            student_stream=student_stream,
            report=report_data,
            previous_exams=previous_exams,
            previous_exam_marks=previous_exam_marks,
            current_exam_title=current_exam_title,
            teacher_map=teacher_map
        )
    except Exception as e:
        logging.error(f"Parent dashboard error: {e}", exc_info=True)
        flash("An error occurred loading the dashboard.", "error")
        return redirect(url_for("parent_login"))
    finally:
        conn.close()


@app.route("/parent/newsletters")
def parent_newsletters():
    if "parent_student_id" not in session:
        return redirect(url_for("parent_login"))
    
    # Get newsletters for this parent's student class
    conn = get_db()
    try:
        student_grade = session.get("parent_grade")
        student_id = session.get("parent_student_id")
        
        logging.info(f"Fetching newsletters for student_id={student_id}, grade={student_grade}")
        
        # Check if portal_announcements table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portal_announcements'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            # Table doesn't exist, return empty list
            logging.warning("portal_announcements table does not exist")
            newsletters = []
        else:
            # Get all newsletters for debugging
            all_newsletters = conn.execute("SELECT * FROM portal_announcements").fetchall()
            logging.info(f"All newsletters in database: {len(all_newsletters)}")
            for nl in all_newsletters:
                logging.info(f"  - ID: {nl[0]}, class_context: {nl[5]}, subject: {nl[2]}")
            
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
            
            logging.info(f"Filtered newsletters for grade {student_grade}: {len(newsletters)}")
        
        return render_template(
            "cloud_parent_newsletters.html",
            newsletters=newsletters,
            school_name=session.get("parent_school_name"),
            student_name=session.get("parent_student_name")
        )
    except Exception as e:
        logging.error(f"Error fetching newsletters: {e}", exc_info=True)
        # Return empty list on error
        return render_template(
            "cloud_parent_newsletters.html",
            newsletters=[],
            school_name=session.get("parent_school_name"),
            student_name=session.get("parent_student_name")
        )
    finally:
        conn.close()


@app.route("/mark_newsletter_viewed/<int:newsletter_id>", methods=["POST"])
def mark_newsletter_viewed(newsletter_id):
    if "parent_student_id" not in session:
        return jsonify({"success": False}), 401
    
    conn = get_db()
    try:
        student_id = session.get("parent_student_id")
        
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


def generate_analytics(report_data, conn, grade):
    """Generate analytics data for parent dashboard including trends, comparisons, and comments"""
    if not report_data or 'current_marks' not in report_data:
        return report_data

    current_marks = report_data['current_marks']

    # Get subjects for this grade
    subjects_config = get_subjects_for_grade(grade)

    # Generate subject analysis
    subject_analysis = []
    subject_names = []
    student_scores = []
    class_averages = []

    for subject in subjects_config:
        subject_key = subject.lower()
        score_key = f"{subject_key}_s"
        current_score = current_marks.get(score_key, 0)

        # Convert to int if it's a string
        try:
            current_score = int(current_score) if current_score else 0
        except (ValueError, TypeError):
            current_score = 0

        # Get class average for this subject (mock data for now, should be calculated from actual data)
        class_average = get_class_average(conn, grade, subject_key)

        # Convert to int if it's a string
        try:
            class_average = int(class_average) if class_average else 0
        except (ValueError, TypeError):
            class_average = 0

        # Calculate trend (mock - should compare with previous exams)
        trend = "stable"
        improvement = 0
        decline = 0

        if current_score > class_average:
            performance = "above_average"
        elif current_score < class_average:
            performance = "below_average"
        else:
            performance = "average"

        subject_analysis.append({
            "name": subject,
            "current_score": current_score,
            "previous_1": current_score - 5,  # Mock previous score
            "previous_2": current_score - 10,  # Mock previous score
            "trend": trend,
            "improvement": improvement,
            "decline": decline,
            "class_average": class_average,
            "performance": performance
        })

        subject_names.append(subject)
        student_scores.append(current_score)
        class_averages.append(class_average)

    # Generate overall trend
    total_points = current_marks.get('total_points', 0)
    # Convert to int if it's a string
    try:
        total_points = int(total_points) if total_points else 0
    except (ValueError, TypeError):
        total_points = 0

    if total_points > 40:
        overall_trend = "improving"
    elif total_points < 30:
        overall_trend = "declining"
    else:
        overall_trend = "stable"

    # Generate comments
    overall_comment = generate_overall_comment(total_points, overall_trend)
    subject_comments = generate_subject_comments(subject_analysis)
    recommendations = generate_recommendations(subject_analysis, total_points)

    # Generate exam labels and scores for trend chart
    exam_labels = ["Exam 3", "Exam 2", "Current Exam"]
    exam_scores = [total_points - 10, total_points - 5, total_points]

    # Add analytics to report data
    report_data['subject_analysis'] = subject_analysis
    report_data['trend'] = overall_trend
    report_data['overall_comment'] = overall_comment
    report_data['subject_comments'] = subject_comments
    report_data['recommendations'] = recommendations
    report_data['exam_labels'] = exam_labels
    report_data['exam_scores'] = exam_scores
    report_data['subject_names'] = subject_names
    report_data['student_scores'] = student_scores
    report_data['class_averages'] = class_averages

    return report_data


def get_subjects_for_grade(grade):
    """Get subjects for a specific grade"""
    grade_mapping = {
        'playgroup': ['LANG', 'MATH', 'ENV', 'CREAT'],
        'pp1': ['LANG', 'MATH', 'ENV', 'PSYCH', 'REL'],
        'pp2': ['LANG', 'MATH', 'ENV', 'PSYCH', 'REL'],
        'Grade 1': ['ENG', 'KISW', 'MAT', 'ENV', 'LIT', 'CRE', 'ART', 'MOV'],
        'Grade 2': ['ENG', 'KISW', 'MAT', 'ENV', 'LIT', 'CRE', 'ART', 'MOV'],
        'Grade 3': ['ENG', 'KISW', 'MAT', 'ENV', 'LIT', 'CRE', 'ART', 'MOV'],
        'Grade 4': ['ENG', 'KISW', 'MATH', 'SCIE', 'AGRI', 'SST', 'CRE', 'C/A', 'PHE'],
        'Grade 5': ['ENG', 'KISW', 'MATH', 'SCIE', 'AGRI', 'SST', 'CRE', 'C/A', 'PHE'],
        'Grade 6': ['ENG', 'KISW', 'MATH', 'SCIE', 'AGRI', 'SST', 'CRE', 'C/A', 'PHE'],
    }
    return grade_mapping.get(grade, [])


def get_class_average(conn, grade, subject):
    """Get class average for a subject (mock implementation)"""
    # In a real implementation, this would calculate from actual student data
    return 50  # Mock average


def generate_overall_comment(total_points, trend):
    """Generate overall performance comment"""
    # Convert to int if it's a string
    try:
        total_points = int(total_points) if total_points else 0
    except (ValueError, TypeError):
        total_points = 0

    if total_points >= 45:
        if trend == "improving":
            return "Excellent performance! The student is showing consistent improvement and maintaining high academic standards. Keep up the outstanding work!"
        else:
            return "Excellent performance! The student is maintaining high academic standards across all subjects."
    elif total_points >= 35:
        if trend == "improving":
            return "Good performance with positive trends. The student is making steady progress and showing improvement in key areas."
        else:
            return "Good performance overall. The student is meeting expectations in most subjects."
    elif total_points >= 25:
        if trend == "declining":
            return "Performance needs attention. The student is showing some decline and may benefit from additional support in certain subjects."
        else:
            return "Satisfactory performance. There is room for improvement, but the student is making effort in their studies."
    else:
        return "Performance requires significant improvement. The student needs additional support and encouragement to reach their full potential."


def generate_subject_comments(subject_analysis):
    """Generate comments for each subject"""
    comments = []
    for subject in subject_analysis:
        score = subject['current_score']
        performance = subject['performance']

        # Convert to int if it's a string
        try:
            score = int(score) if score else 0
        except (ValueError, TypeError):
            score = 0

        if score >= 80:
            comment_type = "positive"
            comment = f"Outstanding performance in {subject['name']}. The student demonstrates excellent understanding and mastery of the subject matter."
        elif score >= 60:
            comment_type = "positive"
            comment = f"Good performance in {subject['name']}. The student shows solid understanding and continues to make progress."
        elif score >= 40:
            comment_type = "neutral"
            comment = f"Satisfactory performance in {subject['name']}. The student meets basic requirements but could benefit from more practice."
        else:
            comment_type = "negative"
            comment = f"Performance in {subject['name']} needs improvement. Additional support and practice are recommended."

        comments.append({
            "subject": subject['name'],
            "comment": comment,
            "type": comment_type
        })

    return comments


def generate_recommendations(subject_analysis, total_points):
    """Generate recommendations for improvement"""
    recommendations = []
    
    # Analyze weak subjects
    weak_subjects = [s for s in subject_analysis if s['current_score'] < 40]
    if weak_subjects:
        recommendations.append(f"Focus additional practice time on: {', '.join([s['name'] for s in weak_subjects])}")
    
    # Analyze strong subjects
    strong_subjects = [s for s in subject_analysis if s['current_score'] >= 70]
    if strong_subjects:
        recommendations.append(f"Continue to excel in: {', '.join([s['name'] for s in strong_subjects])}")
    
    # General recommendations
    if total_points < 30:
        recommendations.append("Consider seeking extra help from teachers or tutors in challenging subjects.")
        recommendations.append("Establish a consistent study routine with dedicated time for each subject.")
    elif total_points < 40:
        recommendations.append("Set specific goals for improvement in each subject.")
        recommendations.append("Review class notes regularly and complete all assignments on time.")
    else:
        recommendations.append("Maintain current study habits and continue to challenge yourself.")
        recommendations.append("Consider helping peers who may be struggling in subjects you excel in.")
    
    return recommendations


@app.route("/parent/logout")
def parent_logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    # Crucial for Railway: Listen on 0.0.0.0 and use the dynamic PORT variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
