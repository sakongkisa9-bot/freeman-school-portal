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
    send_file,
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import json
import csv
import hmac
import io
import math
import tempfile
import uuid
from datetime import datetime, timezone
import logging
from werkzeug.utils import secure_filename
from grading_logic import (
    get_grade_7_8_rating,
    get_grade_4_6_rating,
    calculate_final_level,
)
from teacher_comments import rating_to_comment as get_subject_rating_comment
from cba_logic import (
    absence_mark_for_grade,
    convert_raw_score,
    describe_criterion,
    task_score_bounds,
    validate_tasks,
)
from cbc_engine import (
    RUBRIC_DESCRIPTORS,
    SUBJECT_TO_LEARNING_AREA,
    aggregate_competency,
    rating_from_percentage,
    aggregate_term_competency,
    calculate_milestone_result,
    reporting_bands_for_rating,
    validate_assessment_number,
    validate_curriculum,
    validate_rubric_rating,
)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(PROJECT_DIR, "templates")
app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

# Configure session for Railway (multi-container environment)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-2026")
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("RAILWAY_ENVIRONMENT") is not None
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


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
            if s >= 90:
                return "EE1"
            elif s >= 75:
                return "EE2"
            elif s >= 58:
                return "ME1"
            elif s >= 41:
                return "ME2"
            elif s >= 31:
                return "AE1"
            elif s >= 21:
                return "AE2"
            elif s >= 11:
                return "BE1"
            else:
                return "BE2"
        elif grade_lower in ["grade 1", "grade 2", "grade 3"]:
            # Primary grades
            if s >= 90:
                return "EE1"
            elif s >= 75:
                return "EE2"
            elif s >= 58:
                return "ME1"
            elif s >= 41:
                return "ME2"
            elif s >= 31:
                return "AE1"
            elif s >= 21:
                return "AE2"
            elif s >= 11:
                return "BE1"
            else:
                return "BE2"
        elif grade_lower in ["grade 4", "grade 5", "grade 6"]:
            # Primary grades with different scale
            if s >= 90:
                return "EE1"
            elif s >= 75:
                return "EE2"
            elif s >= 58:
                return "ME1"
            elif s >= 41:
                return "ME2"
            elif s >= 31:
                return "AE1"
            elif s >= 21:
                return "AE2"
            elif s >= 11:
                return "BE1"
            else:
                return "BE2"
        elif grade_lower in ["grade 7", "grade 8", "grade 9"]:
            # Junior Secondary
            if s >= 90:
                return "EE1"
            elif s >= 75:
                return "EE2"
            elif s >= 58:
                return "ME1"
            elif s >= 41:
                return "ME2"
            elif s >= 31:
                return "AE1"
            elif s >= 21:
                return "AE2"
            elif s >= 11:
                return "BE1"
            else:
                return "BE2"
        else:
            # Default
            if s >= 90:
                return "EE1"
            elif s >= 75:
                return "EE2"
            elif s >= 58:
                return "ME1"
            elif s >= 41:
                return "ME2"
            elif s >= 31:
                return "AE1"
            elif s >= 21:
                return "AE2"
            elif s >= 11:
                return "BE1"
            else:
                return "BE2"
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
        "BE2": 1,
    }
    return rating_points.get(rating, 0)


# Custom Jinja2 filter to convert rating to teacher comment
def rating_to_comment(rating, subject=None, subject_comment_indices=None):
    """Convert a rating to the comment set assigned to its subject."""
    return get_subject_rating_comment(rating, subject, subject_comment_indices)


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
        "BE2": "A beginning step in your learning journey. Stay dedicated, and we will work on the fundamentals.",
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
        "BE2": "There is potential for growth. We will provide the support needed to improve next term.",
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
                encoded = base64.b64encode(image_file.read()).decode("utf-8")
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
    if points >= 7.5:
        return "EE1"
    elif points >= 6.5:
        return "EE2"
    elif points >= 5.5:
        return "ME1"
    elif points >= 4.5:
        return "ME2"
    elif points >= 3.5:
        return "AE1"
    elif points >= 2.5:
        return "AE2"
    elif points >= 1.5:
        return "BE1"
    else:
        return "BE2"


# Custom Jinja2 filter to check if string is digit
def isdigit(s):
    """Check if string represents a digit/number"""
    if not s:
        return False
    try:
        int(s)
        return True
    except (ValueError, TypeError):
        return False


app.jinja_env.filters["score_to_rating"] = score_to_rating
app.jinja_env.filters["rating_to_points"] = rating_to_points
app.jinja_env.filters["points_to_rating"] = points_to_rating
app.jinja_env.filters["rating_to_comment"] = rating_to_comment
app.jinja_env.filters["get_class_teacher_comment"] = get_class_teacher_comment
app.jinja_env.filters["get_head_teacher_comment"] = get_head_teacher_comment
app.jinja_env.filters["image_to_base64"] = image_to_base64
app.jinja_env.filters["isdigit"] = isdigit


# Custom filter to remove trailing '_s' suffix only
def rstrip_suffix(s, suffix="_s"):
    """Remove trailing suffix from string"""
    if s.endswith(suffix):
        return s[: -len(suffix)]
    return s


app.jinja_env.filters["rstrip_suffix"] = rstrip_suffix


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
    "Grade 10",
    "Grade 11",
    "Grade 12",
]

GRADE_SUBJECTS = {
    "playgroup": ["LANG", "MATH", "ENV", "CREAT"],
    "pp1": ["LANG", "MATH", "ENV", "PSYCH", "REL"],
    "pp2": ["LANG", "MATH", "ENV", "PSYCH", "REL"],
    "lower": ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"],
    "primary": ["ENG", "KISW", "MATH", "SCIE", "AGRI", "SST", "CRE", "C/A", "PHE"],
    "jss": ["MATH", "ENG", "KISW", "INT SCIE", "PRE-TECH", "SST", "CRE", "AGRI", "C/A"],
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
    "Grade 10": [],
    "Grade 11": [],
    "Grade 12": [],
}
SYSTEM_ADMIN_KEY = "16592@FREE man"


def map_grade_to_config_key(grade):
    """Map portal grade names to config keys used in school_config.json"""
    grade_mapping = {
        "Grade 1": "lower",
        "Grade 2": "lower", 
        "Grade 3": "lower",
        "Grade 4": "primary",
        "Grade 5": "primary",
        "Grade 6": "primary",
        "Grade 7": "jss",
        "Grade 8": "jss",
        "Grade 9": "jss",
    }
    return grade_mapping.get(grade, grade)


def get_db():
    # Ensure database directory exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logging.info(f"Created database directory: {db_dir}")

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    logging.info(f"Database connected at: {DB_PATH}")
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
    if "portal_open" not in columns:
        cursor.execute("ALTER TABLE schools ADD COLUMN portal_open INTEGER DEFAULT 0")
        conn.commit()
    else:
        # Update existing schools to have portal_open = 0 (closed) by default
        cursor.execute("UPDATE schools SET portal_open = 0 WHERE portal_open IS NULL")
        conn.commit()

    # Add school details columns if they don't exist
    cursor.execute("PRAGMA table_info(schools)")
    columns = [column[1] for column in cursor.fetchall()]
    if "school_address" not in columns:
        cursor.execute("ALTER TABLE schools ADD COLUMN school_address TEXT")
        conn.commit()
    if "school_telephone" not in columns:
        cursor.execute("ALTER TABLE schools ADD COLUMN school_telephone TEXT")
        conn.commit()
    if "school_logo" not in columns:
        cursor.execute("ALTER TABLE schools ADD COLUMN school_logo TEXT")
        conn.commit()
    if "subjects" not in columns:
        cursor.execute("ALTER TABLE schools ADD COLUMN subjects TEXT")
        conn.commit()
    if "school_administrator" not in columns:
        cursor.execute("ALTER TABLE schools ADD COLUMN school_administrator TEXT")
        conn.commit()
    if "school_signature" not in columns:
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
    if "photo" not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN photo TEXT")
        conn.commit()
    # Add stream column if it doesn't exist
    if "stream" not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN stream TEXT")
        conn.commit()
    if "assessment_number" not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN assessment_number TEXT")
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
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            scope_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            exam_id INTEGER NOT NULL,
            grade TEXT NOT NULL,
            subject TEXT NOT NULL,
            teacher_code TEXT,
            out_of INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'final')),
            updated_at TEXT NOT NULL,
            UNIQUE (school_id, exam_id, grade, subject)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS global_curriculum (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grade TEXT NOT NULL,
            area TEXT NOT NULL,
            strands_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (grade, area)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cba_task_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            grade TEXT NOT NULL,
            subject TEXT NOT NULL,
            tasks_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(school_id, grade, subject),
            FOREIGN KEY(school_id) REFERENCES schools(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cba_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            grade TEXT NOT NULL,
            subject TEXT NOT NULL,
            adm_no TEXT NOT NULL,
            student_name TEXT NOT NULL,
            task_name TEXT NOT NULL,
            raw_score TEXT NOT NULL,
            teacher_code TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(school_id, grade, subject, adm_no, task_name),
            FOREIGN KEY(school_id) REFERENCES schools(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cba_term_task_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            grade TEXT NOT NULL,
            subject TEXT NOT NULL,
            term TEXT NOT NULL,
            tasks_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(school_id, grade, subject, term),
            FOREIGN KEY(school_id) REFERENCES schools(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cba_term_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            grade TEXT NOT NULL,
            subject TEXT NOT NULL,
            term TEXT NOT NULL,
            adm_no TEXT NOT NULL,
            student_name TEXT NOT NULL,
            task_name TEXT NOT NULL,
            raw_score TEXT NOT NULL,
            teacher_code TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(school_id, grade, subject, term, adm_no, task_name),
            FOREIGN KEY(school_id) REFERENCES schools(id)
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO cba_term_task_configs
            (school_id, grade, subject, term, tasks_json, updated_at)
        SELECT school_id, grade, subject, 'Term 1', tasks_json, updated_at
        FROM cba_task_configs
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO cba_term_scores
            (school_id, grade, subject, term, adm_no, student_name, task_name,
             raw_score, teacher_code, updated_at)
        SELECT school_id, grade, subject, 'Term 1', adm_no, student_name, task_name,
               raw_score, teacher_code, updated_at
        FROM cba_scores
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
        CREATE TABLE IF NOT EXISTS student_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            adm_no TEXT NOT NULL,
            student_name TEXT NOT NULL,
            payment_type TEXT NOT NULL,
            amount_paid REAL NOT NULL,
            payment_status TEXT DEFAULT 'pending',
            payment_date TEXT,
            notification_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(adm_no, payment_type)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_payment_amount REAL NOT NULL,
            payment_percentage REAL DEFAULT 70.0,
            payment_option TEXT DEFAULT 'full',
            system_locked INTEGER DEFAULT 0,
            phone_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    with open(os.path.join(PROJECT_DIR, "001_cbc_assessment.sql"), encoding="utf-8") as migration:
        conn.executescript(migration.read())
    rubric_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(cbc_rubric_scores)")
    }
    if "assessment_type" not in rubric_columns:
        conn.executescript(
            """
            BEGIN;
            ALTER TABLE cbc_rubric_scores RENAME TO cbc_rubric_scores_legacy;
            CREATE TABLE cbc_rubric_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id INTEGER NOT NULL,
                grade TEXT NOT NULL,
                assessment_number TEXT NOT NULL,
                academic_year INTEGER NOT NULL,
                term TEXT NOT NULL,
                assessment_type TEXT NOT NULL CHECK (assessment_type IN ('Formative', 'Localized Summative')),
                sub_strand_id INTEGER NOT NULL,
                rating TEXT NOT NULL CHECK (rating IN ('1', '2', '3', '4', 'AB')),
                evidence TEXT,
                teacher_code TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE (school_id, grade, assessment_number, academic_year, term, assessment_type, sub_strand_id),
                FOREIGN KEY (sub_strand_id) REFERENCES cbc_sub_strands(id)
            );
            INSERT INTO cbc_rubric_scores
                (id, school_id, grade, assessment_number, academic_year, term, assessment_type,
                 sub_strand_id, rating, evidence, teacher_code, updated_at)
            SELECT id, school_id, grade, assessment_number, academic_year, term, 'Formative',
                   sub_strand_id, rating, evidence, teacher_code, updated_at
            FROM cbc_rubric_scores_legacy;
            DROP TABLE cbc_rubric_scores_legacy;
            CREATE INDEX IF NOT EXISTS idx_cbc_rubric_assessment
            ON cbc_rubric_scores (school_id, grade, assessment_number, academic_year, term);
            COMMIT;
            """
        )
    milestone_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(cbc_milestone_results)")
    }
    for column in ("grade7_sba_percent", "grade8_sba_percent"):
        if column not in milestone_columns:
            conn.execute(f"ALTER TABLE cbc_milestone_results ADD COLUMN {column} REAL")
    conn.commit()
    conn.close()


def authenticate_user(school_code, username, password, teacher_code=None):
    conn = get_db()
    # Normalize school_code to lowercase to match your register logic
    sc = school_code.strip().lower()
    print(
        f"[DEBUG] authenticate_user: school_code={sc}, username={username}, teacher_code={teacher_code}"
    )

    school = conn.execute(
        "SELECT * FROM schools WHERE school_code = ?", (sc,)
    ).fetchone()
    print(f"[DEBUG] school query result: {school}")

    if not school:
        conn.close()
        return None, "School code not found."

    # Verify password against school password (all teachers use school credentials)
    if not check_password_hash(school["password_hash"], password):
        print(f"[DEBUG] Password hash mismatch")
        conn.close()
        return None, "Invalid username or password."

    # If teacher_code is provided, verify teacher exists in teacher_assignments
    if teacher_code:
        teacher = conn.execute(
            "SELECT * FROM teacher_assignments WHERE school_id = ? AND teacher_code = ?",
            (school["id"], teacher_code.strip()),
        ).fetchone()
        print(f"[DEBUG] teacher query result: {teacher}")
        if not teacher:
            conn.close()
            return None, "Invalid teacher code."

        print(f"[DEBUG] Authentication successful")
        return {"school": school, "teacher": teacher}, None

    print(f"[DEBUG] Authentication successful (school admin)")
    return {"school": school, "teacher": None}, None


def is_admin():
    return session.get("role") == "admin"


def check_fcm_registration():
    """Check FCM service registration status on startup"""
    try:
        from fcm_service import get_fcm_service

        logging.info("=== FCM REGISTRATION CHECK STARTUP ===")
        fcm_service = get_fcm_service()

        if fcm_service.is_available():
            logging.info("✓ FCM Service is available and initialized")
            # Check database for FCM tokens table
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='fcm_tokens'"
            )
            table_exists = cursor.fetchone()

            if table_exists:
                cursor.execute("SELECT COUNT(*) as count FROM fcm_tokens")
                token_count = cursor.fetchone()["count"]
                logging.info(
                    f"✓ FCM tokens table exists with {token_count} registered tokens"
                )
            else:
                logging.warning("⚠ FCM tokens table does not exist in database")

            conn.close()
        else:
            logging.warning(
                "⚠ FCM Service is not available - notifications will be disabled"
            )
            logging.warning(
                "  To enable FCM, set FIREBASE_SERVICE_ACCOUNT environment variable"
            )
            logging.warning("  or place firebase-service-account.json in project root")

        logging.info("=== FCM REGISTRATION CHECK COMPLETE ===")

    except Exception as e:
        logging.error(f"Error during FCM registration check: {e}")


init_db()
check_fcm_registration()


@app.route("/")
def home():
    # Show role selection page
    return render_template("cloud_home.html")


@app.route("/about")
def about():
    # About Us page
    return render_template("cloud_about.html")


@app.route("/privacy")
def privacy():
    # Privacy Policy page
    return render_template("cloud_privacy.html")


@app.route("/terms")
def terms():
    # Terms of Use page
    return render_template("cloud_terms.html")


@app.route("/contact")
def contact():
    # Contact page
    return render_template("cloud_contact.html")


@app.route("/firebase-messaging-sw.js")
def serve_firebase_sw():
    """Serve the Firebase Cloud Messaging service worker"""
    return send_from_directory("static", "firebase-messaging-sw.js")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Check the Master Key first
        master_key = request.form.get("master_key")
        if master_key != SYSTEM_ADMIN_KEY:
            session.pop('_flashes', None)
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
            session.pop('_flashes', None)
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
        conn.execute(
            "DELETE FROM marks WHERE school_id = (SELECT id FROM schools WHERE school_code = ?)",
            (school_code,),
        )
        # Delete students
        conn.execute(
            "DELETE FROM students WHERE school_id = (SELECT id FROM schools WHERE school_code = ?)",
            (school_code,),
        )
        # Delete teachers
        conn.execute(
            "DELETE FROM teachers WHERE school_id = (SELECT id FROM schools WHERE school_code = ?)",
            (school_code,),
        )
        # Delete school
        conn.execute("DELETE FROM schools WHERE school_code = ?", (school_code,))
        conn.commit()
        session.pop('_flashes', None)
        flash(f"School '{school_code}' deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        session.pop('_flashes', None)
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
                session.pop('_flashes', None)
                flash("School name is required.", "danger")
                return redirect(url_for("admin_edit_school", school_code=school_code))

            # Convert signature to base64 if uploaded
            signature_base64 = None
            if signature_file and signature_file.filename:
                import base64

                signature_data = signature_file.read()
                signature_base64 = base64.b64encode(signature_data).decode("utf-8")
                # Determine mime type
                ext = signature_file.filename.lower().split(".")[-1]
                mime_type = "image/png" if ext == "png" else "image/jpeg"
                signature_base64 = f"data:{mime_type};base64,{signature_base64}"

            if password:
                # Update password if provided
                password_hash = generate_password_hash(password)
                conn.execute(
                    "UPDATE schools SET school_name = ?, email = ?, password_hash = ?, school_administrator = ? WHERE school_code = ?",
                    (
                        school_name,
                        email,
                        password_hash,
                        school_administrator,
                        school_code,
                    ),
                )
            else:
                # Update only name and email
                conn.execute(
                    "UPDATE schools SET school_name = ?, email = ?, school_administrator = ? WHERE school_code = ?",
                    (school_name, email, school_administrator, school_code),
                )

            # Update signature if uploaded
            if signature_base64:
                conn.execute(
                    "UPDATE schools SET school_signature = ? WHERE school_code = ?",
                    (signature_base64, school_code),
                )

            conn.commit()
            session.pop('_flashes', None)
            flash(f"School '{school_code}' updated successfully.", "success")
            return redirect(url_for("admin_schools"))
        except Exception as e:
            conn.rollback()
            session.pop('_flashes', None)
            flash(f"Error updating school: {e}", "danger")
        finally:
            conn.close()
    else:
        school = conn.execute(
            "SELECT * FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()
        conn.close()
        if not school:
            session.pop('_flashes', None)
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

            print(
                f"[DEBUG] Teacher login attempt: school_code={sc}, username={un}, teacher_code={teacher_code}"
            )

            auth, err = authenticate_user(sc, un, pw, teacher_code)
            if err:
                print(f"[DEBUG] Authentication failed: {err}")
                session.pop('_flashes', None)
                flash(err, "danger")
                return redirect(url_for("teacher_login"))

            print(f"[DEBUG] Authentication successful: {auth}")

            # Convert the Row objects to real dictionaries so .get() works elsewhere
            school_data = dict(auth["school"])
            teacher_data = dict(auth["teacher"]) if auth["teacher"] else None

            print(f"[DEBUG] school_data: {school_data}, teacher_data: {teacher_data}")

            session["school_id"] = school_data["id"]
            session["school_name"] = school_data["school_name"]
            session["username"] = un  # Use the username from login form (school email)
            session["role"] = "teacher"
            session["teacher_code"] = teacher_code

            print(f"[DEBUG] Login successful, redirecting to dashboard")
            return redirect(url_for("dashboard"))

    except Exception as e:
        # This will tell us exactly which key is missing if it happens again
        print(f"[DEBUG] Exception in teacher_login: {e}")
        return f"Database Error: {str(e)}"

    return render_template("cloud_login.html")


@app.route("/dashboard")
def dashboard():
    print(f"[DEBUG] Dashboard accessed, session keys: {list(session.keys())}")
    if "school_id" not in session:
        print(f"[DEBUG] school_id not in session, redirecting to login")
        return redirect(url_for("teacher_login"))

    conn = get_db()
    school = conn.execute(
        "SELECT portal_open, school_name FROM schools WHERE id = ?",
        (session["school_id"],),
    ).fetchone()

    # Get teacher name if teacher_code is in session
    teacher_name = None
    if session.get("teacher_code"):
        teacher = conn.execute(
            "SELECT teacher_name FROM teacher_assignments WHERE school_id = ? AND teacher_code = ?",
            (session["school_id"], session["teacher_code"]),
        ).fetchone()
        if teacher:
            teacher_name = teacher["teacher_name"]

    teacher_code = session.get("teacher_code")
    visible_grades = list(GRADE_OPTIONS)
    exam = _current_exam(conn, session["school_id"])
    exam_grades = set()
    if teacher_code:
        assigned_classes = {
            row["class_name"]
            for row in conn.execute(
                "SELECT DISTINCT class_name FROM teacher_assignments WHERE school_id = ? AND teacher_code = ?",
                (session["school_id"], teacher_code),
            ).fetchall()
        }
        visible_grades = [grade for grade in GRADE_OPTIONS if grade in assigned_classes]
        for grade in visible_grades:
            if _open_exam_subjects(conn, session["school_id"], grade, teacher_code)[1]:
                exam_grades.add(grade)

    conn.close()

    portal_open = school["portal_open"] if school else 1
    school_name = (
        school["school_name"] if school else session.get("school_name", "Your School")
    )
    return render_template(
        "cloud_dashboard.html",
        grades=visible_grades,
        portal_open=portal_open,
        school_name=school_name,
        teacher_name=teacher_name,
        is_admin=is_admin(),
        is_teacher=bool(teacher_code),
        exam=exam,
        exam_grades=exam_grades,
    )


@app.route("/api/toggle_portal", methods=["POST"])
def api_toggle_portal():
    # API key authentication (like sync endpoints)
    data = request.json
    school_code = data.get("school_code", "").strip().lower()
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    print(f"[DEBUG] toggle_portal: school_code={school_code}, username={username}")

    if not school_code or not username or not password:
        return jsonify({"success": False, "message": "Missing credentials"}), 400

    conn = get_db()
    try:
        # Authenticate school
        school = conn.execute(
            "SELECT * FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()

        print(f"[DEBUG] school query result: {school}")

        if not school:
            return jsonify({"success": False, "message": "School not found"}), 404

        # Verify password against school password
        if not check_password_hash(school["password_hash"], password):
            return jsonify({"success": False, "message": "Invalid password"}), 401

        # Get current portal state
        current_state = school["portal_open"]

        # Toggle portal state
        new_state = 0 if current_state == 1 else 1
        conn.execute(
            "UPDATE schools SET portal_open = ? WHERE id = ?", (new_state, school["id"])
        )
        conn.commit()

        return jsonify(
            {
                "success": True,
                "portal_open": new_state,
                "message": "Portal opened" if new_state == 1 else "Portal closed",
            }
        )
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
                SET school_address = ?, school_telephone = ?, school_logo = ?, subjects = ?
                WHERE id = ?
            """,
                (
                    school_details.get("school_address"),
                    school_details.get("school_telephone"),
                    school_details.get("school_logo"),
                    json.dumps(school_details.get("subjects", {})),
                    school_id,
                ),
            )

        # 3. Delete all existing students for this school
        conn.execute("DELETE FROM students WHERE school_id = ?", (school_id,))

        # 4. Insert new students
        for s in students_list:
            conn.execute(
                """
                INSERT INTO students (school_id, grade, adm_no, student_name, gender, phone, photo, stream, assessment_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    s.get("assessment_number", ""),
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
        conn.execute(
            "DELETE FROM teacher_assignments WHERE school_id = ?", (school_id,)
        )

        # 3. Insert new teacher assignments
        for t in teachers_list:
            print(f"[DEBUG] Processing teacher: {t}")
            # Insert into teacher_assignments
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


@app.route("/api/upload_cba_tasks", methods=["POST"])
def api_upload_cba_tasks():
    data = request.get_json(silent=True) or {}
    school_code = str(data.get("school_code", "")).strip().lower()
    password = data.get("password", "")
    grade = str(data.get("grade", "")).strip()
    subject = str(data.get("subject", "")).strip()
    term = str(data.get("term", "Term 1")).strip() or "Term 1"
    try:
        tasks = validate_tasks(data.get("tasks"))
    except ValueError as error:
        return jsonify({"success": False, "message": str(error)}), 400

    if not school_code or not password or not grade or not subject:
        return jsonify({"success": False, "message": "Missing school credentials or class/subject."}), 400

    conn = get_db()
    try:
        school = conn.execute(
            "SELECT id, password_hash FROM schools WHERE school_code = ?",
            (school_code,),
        ).fetchone()
        if not school or not check_password_hash(school["password_hash"], password):
            return jsonify({"success": False, "message": "Invalid school credentials."}), 401

        conn.execute(
            """
            INSERT INTO cba_term_task_configs
                (school_id, grade, subject, term, tasks_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(school_id, grade, subject, term) DO UPDATE SET
                tasks_json = excluded.tasks_json,
                updated_at = excluded.updated_at
            """,
            (
                school["id"],
                grade,
                subject,
                term,
                json.dumps(tasks),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return jsonify({"success": True, "message": "CBA tasks published."})
    except Exception as error:
        conn.rollback()
        logging.exception("CBA task publish failed")
        return jsonify({"success": False, "message": str(error)}), 500
    finally:
        conn.close()


@app.route("/api/cbc/fetch_covered_strands", methods=["POST"])
def api_fetch_cbc_covered_strands():
    data = request.get_json(silent=True) or {}
    school_code = str(data.get("school_code", "")).strip().lower()
    password = data.get("password", "")
    grade = str(data.get("grade", "")).strip()
    area_name = str(data.get("area", "")).strip()
    try:
        academic_year = int(data.get("academic_year"))
        if not 2000 <= academic_year <= 2200:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid academic year."}), 400
    if not school_code or not password or not grade or not area_name:
        return jsonify({"success": False, "message": "Missing school credentials or class."}), 400

    conn = get_db()
    try:
        school = conn.execute(
            "SELECT id, password_hash FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()
        if not school or not check_password_hash(school["password_hash"], password):
            return jsonify({"success": False, "message": "Invalid school credentials."}), 401
        curriculum = conn.execute(
            "SELECT strands_json FROM global_curriculum WHERE grade = ? AND area = ?",
            (grade, area_name),
        ).fetchone()
        if not curriculum:
            return jsonify({
                "success": False,
                "message": f"No strands have been uploaded to the portal for {area_name} in {grade} yet.",
            })
        covered = {}
        for row in conn.execute(
            """
            SELECT st.name AS strand, ss.name AS sub_strand, GROUP_CONCAT(DISTINCT rs.term) AS terms
            FROM cbc_rubric_scores rs
            JOIN cbc_sub_strands ss ON ss.id = rs.sub_strand_id
            JOIN cbc_strands st ON st.id = ss.strand_id
            JOIN cbc_learning_areas la ON la.id = st.learning_area_id
            WHERE rs.school_id = ? AND rs.grade = ? AND rs.academic_year = ?
              AND rs.assessment_type = 'Formative' AND la.name = ?
            GROUP BY st.name, ss.name
            """,
            (school["id"], grade, academic_year, area_name),
        ).fetchall():
            covered[(row["strand"], row["sub_strand"])] = sorted(row["terms"].split(","))
        strands = [
            {
                "name": strand["name"],
                "sub_strands": [
                    {"name": name, "terms": covered.get((strand["name"], name), [])}
                    for name in strand["sub_strands"]
                ],
            }
            for strand in json.loads(curriculum["strands_json"])
        ]
        return jsonify({
            "success": True,
            "grade": grade,
            "area": area_name,
            "academic_year": academic_year,
            "strands": strands,
        })
    except Exception as error:
        logging.exception("CBC covered strands fetch failed")
        return jsonify({"success": False, "message": str(error)}), 500
    finally:
        conn.close()


@app.route("/api/cbc/fetch_ratings", methods=["POST"])
def api_fetch_cbc_ratings():
    data = request.get_json(silent=True) or {}
    school_code = str(data.get("school_code", "")).strip().lower()
    password = data.get("password", "")
    grade = str(data.get("grade", "")).strip()
    area = str(data.get("area", "")).strip()
    term = str(data.get("term", "Term 1")).strip()
    try:
        academic_year = int(data.get("academic_year"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter a valid academic year."}), 400
    if not school_code or not password or not grade or not area:
        return jsonify({"success": False, "message": "Missing school credentials, class, or learning area."}), 400
    if term not in {"Term 1", "Term 2", "Term 3"}:
        return jsonify({"success": False, "message": "Invalid term."}), 400
    if academic_year < 2000 or academic_year > 2200:
        return jsonify({"success": False, "message": "Invalid academic year."}), 400

    conn = get_db()
    try:
        school = conn.execute(
            "SELECT id, password_hash FROM schools WHERE school_code = ?",
            (school_code,),
        ).fetchone()
        if not school or not check_password_hash(school["password_hash"], password):
            return jsonify({"success": False, "message": "Invalid school credentials."}), 401
        query = """
            SELECT rs.assessment_number, COALESCE(students.student_name, ''),
                   la.name, st.name, ss.name, rs.rating
            FROM cbc_rubric_scores rs
            JOIN cbc_sub_strands ss ON ss.id = rs.sub_strand_id
            JOIN cbc_strands st ON st.id = ss.strand_id
            JOIN cbc_learning_areas la ON la.id = st.learning_area_id
            LEFT JOIN students ON students.school_id = rs.school_id
                AND students.grade = rs.grade
                AND students.assessment_number = rs.assessment_number
            WHERE rs.school_id = ? AND rs.grade = ? AND la.name = ?
                AND rs.term = ? AND rs.academic_year = ?
                AND rs.assessment_type = 'Formative'
        """
        parameters = [school["id"], grade, area, term, academic_year]
        query += " ORDER BY st.id, ss.id, students.student_name COLLATE NOCASE"
        rows = conn.execute(query, parameters).fetchall()
        records = []
        for row in rows:
            level = row[5]
            if level.isdigit():
                level = RUBRIC_DESCRIPTORS.get(int(level), level)
            records.append([*row[:5], level])
        return jsonify(
            {
                "success": True,
                "columns": [
                    "Assessment Number",
                    "Learner",
                    "Learning Area",
                    "Strand",
                    "Sub-strand",
                    "Level",
                ],
                "records": records,
                "grade": grade,
                "area": area,
                "term": term,
                "academic_year": academic_year,
            }
        )
    except Exception as error:
        logging.exception("CBC ratings fetch failed")
        return jsonify({"success": False, "message": str(error)}), 500
    finally:
        conn.close()


RATING_POINTS = {"EE1": 8, "EE2": 7, "ME1": 6, "ME2": 5, "AE1": 4, "AE2": 3, "BE1": 2, "BE2": 1}


def _current_exam(conn, school_id):
    return conn.execute(
        "SELECT id, title, scope_json FROM exams WHERE school_id = ? ORDER BY id DESC LIMIT 1",
        (school_id,),
    ).fetchone()


def _exam_covers_grade(exam, grade):
    try:
        scope = json.loads(exam["scope_json"])
    except (TypeError, ValueError):
        return False
    return bool(scope.get("all")) or grade in scope.get("classes", [])


def _open_exam_subjects(conn, school_id, grade, teacher_code):
    """Return the current exam and the teacher's subjects in this class that are not finished."""
    exam = _current_exam(conn, school_id)
    if not exam or not teacher_code or not _exam_covers_grade(exam, grade):
        return exam, []
    assigned = [
        row["subject"]
        for row in conn.execute(
            "SELECT DISTINCT subject FROM teacher_assignments WHERE school_id = ? AND class_name = ? AND teacher_code = ? ORDER BY subject",
            (school_id, grade, teacher_code),
        ).fetchall()
    ]
    finished = {
        row["subject"]
        for row in conn.execute(
            "SELECT subject FROM exam_submissions WHERE school_id = ? AND exam_id = ? AND grade = ? AND status = 'final'",
            (school_id, exam["id"], grade),
        ).fetchall()
    }
    return exam, [subject for subject in assigned if subject not in finished]


def _parse_exam_marks(out_of_text, raw_values):
    """Validate the out-of total and raw marks; return (out_of, {adm_no: percent or None})."""
    try:
        out_of = int(out_of_text)
        if not 1 <= out_of <= 1000:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Enter the total marks (out of) as a whole number from 1 to 1000.")
    percents = {}
    for adm_no, raw in raw_values.items():
        if raw == "":
            percents[adm_no] = None
            continue
        try:
            value = float(raw)
        except ValueError:
            raise ValueError(f"Marks must be numbers. Check the entry for ADM {adm_no}.")
        if not math.isfinite(value) or not 0 <= value <= out_of:
            raise ValueError(f"Marks must be between 0 and {out_of}. Check the entry for ADM {adm_no}.")
        percents[adm_no] = int(math.floor(value * 100 / out_of + 0.5))
    return out_of, percents


def _store_student_subject_score(conn, school_id, grade, subject, exam_title, student, score, now, extra=None):
    """Save one learner's subject score in the marks table, keeping other subjects intact."""
    is_jss = any(g in grade.lower() for g in ["grade 7", "grade 8", "grade 9"])
    rating = ""
    points = 0
    if score and score.strip():
        try:
            score_int = int(score)
            if is_jss:
                rating, points = get_grade_7_8_rating(score_int)
            else:
                rating = get_grade_4_6_rating(score_int)
                points = RATING_POINTS.get(rating, 0)
        except ValueError:
            rating = ""
            points = 0

    existing = conn.execute(
        "SELECT subject_scores_json FROM marks WHERE school_id=? AND grade=? AND adm_no=? AND exam_title=?",
        (school_id, grade, student["adm_no"], exam_title),
    ).fetchone()
    scores = json.loads(existing["subject_scores_json"]) if existing else {}
    scores[subject] = {"score": score, "rating": rating, "points": points, **(extra or {})}

    total_points = 0
    for data in scores.values():
        if is_jss:
            total_points += int(data.get("points") or 0)
        elif data.get("score"):
            try:
                total_points += int(data["score"])
            except ValueError:
                pass
    avg_level = calculate_final_level(
        total_points, is_primary=not is_jss, num_subjects=len(scores)
    )
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
        (school_id, grade, student["adm_no"], student["student_name"], exam_title,
         json.dumps(scores), str(total_points), avg_level, now),
    )


@app.route("/api/create_exam", methods=["POST"])
def api_create_exam():
    data = request.get_json(silent=True) or {}
    school_code = str(data.get("school_code", "")).strip().lower()
    password = data.get("password", "")
    title = str(data.get("title", "")).strip()
    all_classes = bool(data.get("all_classes"))
    classes = list(dict.fromkeys(str(item).strip() for item in data.get("classes") or [] if str(item).strip()))
    if not school_code or not password:
        return jsonify({"success": False, "message": "Missing school credentials."}), 400
    if not title or len(title) > 120:
        return jsonify({"success": False, "message": "Enter an exam title of up to 120 characters."}), 400
    if not all_classes and (not classes or any(item not in GRADE_OPTIONS for item in classes)):
        return jsonify({"success": False, "message": "Choose all classes or at least one valid class."}), 400

    conn = get_db()
    try:
        school = conn.execute(
            "SELECT id, password_hash FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()
        if not school or not check_password_hash(school["password_hash"], password):
            return jsonify({"success": False, "message": "Invalid school credentials."}), 401
        # A new exam replaces the previous one and clears its marks from the portal.
        conn.execute("DELETE FROM exam_submissions WHERE school_id = ?", (school["id"],))
        conn.execute("DELETE FROM exams WHERE school_id = ?", (school["id"],))
        conn.execute("DELETE FROM marks WHERE school_id = ?", (school["id"],))
        conn.execute(
            "INSERT INTO exams (school_id, title, scope_json, created_at) VALUES (?, ?, ?, ?)",
            (school["id"], title, json.dumps({"all": all_classes, "classes": [] if all_classes else classes}),
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return jsonify({"success": True, "message": f"Exam '{title}' is now live on the portal."})
    except Exception as error:
        conn.rollback()
        logging.exception("Exam creation failed")
        return jsonify({"success": False, "message": str(error)}), 500
    finally:
        conn.close()


@app.route("/exam/select_subject/<grade>")
def select_exam_subject(grade):
    if "school_id" not in session:
        return redirect(url_for("teacher_login"))
    conn = get_db()
    exam, subjects = _open_exam_subjects(
        conn, session["school_id"], grade, session.get("teacher_code")
    )
    conn.close()
    if not subjects:
        flash("No exam marks are open for you in this class.", "warning")
        return redirect(url_for("dashboard"))
    return render_template(
        "cloud_select_subject.html", grade=grade, subjects=subjects, mode="exam",
        exam_title=exam["title"],
    )


@app.route("/exam/marks/<grade>", methods=["GET", "POST"])
def enter_exam_marks(grade):
    if "school_id" not in session:
        return redirect(url_for("teacher_login"))
    subject = request.args.get("subject", "").strip()
    conn = get_db()
    school = conn.execute(
        "SELECT portal_open FROM schools WHERE id = ?", (session["school_id"],)
    ).fetchone()
    if not school or school["portal_open"] == 0:
        conn.close()
        flash("The teachers portal is currently closed. Please contact your administrator.", "danger")
        return redirect(url_for("dashboard"))
    exam, open_subjects = _open_exam_subjects(
        conn, session["school_id"], grade, session.get("teacher_code")
    )
    if subject not in open_subjects:
        conn.close()
        flash("This exam is not open for you in this class and subject, or it is already finished.", "warning")
        return redirect(url_for("dashboard"))

    students = conn.execute(
        "SELECT adm_no, student_name FROM students WHERE school_id = ? AND grade = ? ORDER BY student_name COLLATE NOCASE",
        (session["school_id"], grade),
    ).fetchall()
    submission = conn.execute(
        "SELECT out_of FROM exam_submissions WHERE school_id = ? AND exam_id = ? AND grade = ? AND subject = ?",
        (session["school_id"], exam["id"], grade, subject),
    ).fetchone()
    review = request.args.get("review") == "1" and submission is not None
    out_of_value = str(submission["out_of"]) if submission else ""
    raw_values = {}

    if request.method == "POST":
        action = request.form.get("action")
        review = request.form.get("review") == "1"
        out_of_value = request.form.get("out_of", "").strip()
        raw_values = {
            student["adm_no"]: request.form.get(f"score_{student['adm_no']}", "").strip()
            for student in students
        }
        try:
            out_of, percents = _parse_exam_marks(out_of_value, raw_values)
            if action == "finish" and all(value is None for value in percents.values()):
                raise ValueError("Enter at least one mark before finishing.")
        except ValueError as error:
            flash(str(error), "danger")
        else:
            now = datetime.utcnow().isoformat()
            for student in students:
                percent = percents[student["adm_no"]]
                _store_student_subject_score(
                    conn, session["school_id"], grade, subject, exam["title"], student,
                    "" if percent is None else str(percent), now,
                    {"raw": raw_values[student["adm_no"]], "out_of": out_of},
                )
            conn.execute(
                """
                INSERT INTO exam_submissions (school_id, exam_id, grade, subject, teacher_code, out_of, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(school_id, exam_id, grade, subject) DO UPDATE SET
                teacher_code = excluded.teacher_code, out_of = excluded.out_of,
                status = excluded.status, updated_at = excluded.updated_at
                """,
                (session["school_id"], exam["id"], grade, subject, session.get("teacher_code"),
                 out_of, "final" if action == "finish" else "draft", now),
            )
            conn.commit()
            conn.close()
            if action == "finish":
                flash(f"{subject} marks for {grade} are finished and locked.", "success")
                return redirect(url_for("dashboard"))
            flash("Marks saved. Review them, edit if needed, then click Finish.", "success")
            return redirect(url_for("enter_exam_marks", grade=grade, subject=subject, review=1))

    if not raw_values:
        for row in conn.execute(
            "SELECT adm_no, subject_scores_json FROM marks WHERE school_id = ? AND grade = ? AND exam_title = ?",
            (session["school_id"], grade, exam["title"]),
        ).fetchall():
            entry = json.loads(row["subject_scores_json"]).get(subject)
            if isinstance(entry, dict):
                raw_values[row["adm_no"]] = entry.get("raw", entry.get("score", "")) or ""
    conn.close()
    return render_template(
        "cloud_exam_marks.html",
        grade=grade,
        subject=subject,
        exam_title=exam["title"],
        students=students,
        raw_values=raw_values,
        out_of_value=out_of_value,
        review=review,
    )


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
        session.pop('_flashes', None)
        flash(
            "The teachers portal is currently closed. Please contact your administrator.",
            "danger",
        )
        return redirect(url_for("dashboard"))

    # Verify teacher code for this specific subject
    teacher_code = session.get("teacher_code")
    if not teacher_code:
        conn.close()
        session.pop('_flashes', None)
        flash("Teacher code not found. Please login again.", "danger")
        return redirect(url_for("teacher_login"))

    # Check if the teacher's code is assigned to this subject for this grade
    teacher_assignment = conn.execute(
        "SELECT * FROM teacher_assignments WHERE school_id = ? AND class_name = ? AND subject = ? AND teacher_code = ?",
        (session["school_id"], grade, subject, teacher_code),
    ).fetchone()

    if not teacher_assignment:
        conn.close()
        session.pop('_flashes', None)
        flash(
            f"You are not authorized to enter marks for {subject} in {grade}. Your teacher code does not match.",
            "danger",
        )
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
                        level_points = {
                            "EE1": 8,
                            "EE2": 7,
                            "ME1": 6,
                            "ME2": 5,
                            "AE1": 4,
                            "AE2": 3,
                            "BE1": 2,
                            "BE2": 1,
                        }
                        points = level_points.get(rating, 0)
                    else:
                        # For early years (playgroup, pp1, pp2), use primary logic as fallback
                        rating = get_grade_4_6_rating(score_int)
                        level_points = {
                            "EE1": 8,
                            "EE2": 7,
                            "ME1": 6,
                            "ME2": 5,
                            "AE1": 4,
                            "AE2": 3,
                            "BE1": 2,
                            "BE2": 1,
                        }
                        points = level_points.get(rating, 0)
                except ValueError:
                    rating = ""
                    points = 0

            # 3. Update the specific subject with score, rating, and points
            scores[subject] = {"score": score, "rating": rating, "points": points}

            # 4. Calculate total points and average level across all subjects
            num_subjects = len(scores)
            if is_jss:
                # JSS uses points sum for total
                total_points = 0
                for subj, data in scores.items():
                    if data.get("points"):
                        total_points += int(data["points"])
                avg_level = calculate_final_level(
                    total_points, is_primary=False, num_subjects=num_subjects
                )
            else:
                # Other grades use raw score sum for total
                total_points = 0
                for subj, data in scores.items():
                    if data.get("score"):
                        try:
                            total_points += int(data["score"])
                        except ValueError:
                            pass
                avg_level = calculate_final_level(
                    total_points, is_primary=True, num_subjects=num_subjects
                )

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
        session.pop('_flashes', None)
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

    conn = get_db()
    try:
        # Get the school details including synced subjects from database
        school = conn.execute(
            "SELECT subjects FROM schools WHERE id = ?", (session["school_id"],)
        ).fetchone()
        conn.close()

        subjects = []

        # First, try to get subjects from the database
        if school and school["subjects"]:
            try:
                subjects_data = json.loads(school["subjects"])
                # subjects_data is a dict like {grade: [subjects]}
                # Map grade name to config key (e.g., "Grade 1" -> "lower")
                config_key = map_grade_to_config_key(grade)
                subjects = subjects_data.get(config_key, [])
                # If not found with mapped key, try original grade name
                if not subjects:
                    subjects = subjects_data.get(grade, [])
            except (json.JSONDecodeError, TypeError):
                # If JSON parsing fails, fall back to hardcoded
                subjects = []

        # If no subjects found in database, fall back to hardcoded GRADE_SUBJECTS
        if not subjects:
            subjects = GRADE_SUBJECTS.get(grade, [])

        if not subjects:
            session.pop('_flashes', None)
            flash(f"No subjects configured for {grade}.", "warning")
            return redirect(url_for("dashboard"))

        return render_template(
            "cloud_select_subject.html", grade=grade, subjects=subjects
        )
    except Exception as e:
        logging.error(f"Error retrieving subjects for grade {grade}: {e}")
        # Fall back to hardcoded subjects if there's an error
        subjects = GRADE_SUBJECTS.get(grade, [])
        if not subjects:
            session.pop('_flashes', None)
            flash(f"No subjects configured for {grade}.", "warning")
            return redirect(url_for("dashboard"))
        return render_template(
            "cloud_select_subject.html", grade=grade, subjects=subjects
        )
    finally:
        if conn:
            conn.close()


@app.route("/cba/select_subject/<grade>")
def select_cba_subject(grade):
    if "school_id" not in session:
        return redirect(url_for("teacher_login"))
    teacher_code = session.get("teacher_code")
    if not teacher_code:
        session.pop('_flashes', None)
        flash("Teacher code not found. Please login again.", "danger")
        return redirect(url_for("teacher_login"))

    conn = get_db()
    subjects = [
        row["subject"]
        for row in conn.execute(
            "SELECT subject FROM teacher_assignments WHERE school_id = ? AND class_name = ? AND teacher_code = ? ORDER BY subject",
            (session["school_id"], grade, teacher_code),
        ).fetchall()
    ]
    conn.close()
    if not subjects:
        session.pop('_flashes', None)
        flash(f"No subjects are assigned to you for {grade}.", "warning")
        return redirect(url_for("dashboard"))
    return render_template(
        "cloud_select_subject.html", grade=grade, subjects=subjects, mode="cba"
    )


@app.route("/cba/marks/<grade>", methods=["GET", "POST"])
def enter_cba_marks(grade):
    if "school_id" not in session:
        return redirect(url_for("teacher_login"))
    subject = request.args.get("subject", "").strip()
    teacher_code = session.get("teacher_code")
    if not subject or not teacher_code:
        session.pop('_flashes', None)
        flash("Choose an assigned subject to enter CBA scores.", "danger")
        return redirect(url_for("select_cba_subject", grade=grade))

    conn = get_db()
    school = conn.execute(
        "SELECT portal_open FROM schools WHERE id = ?", (session["school_id"],)
    ).fetchone()
    if not school or school["portal_open"] == 0:
        conn.close()
        session.pop('_flashes', None)
        flash("The teachers portal is currently closed.", "danger")
        return redirect(url_for("dashboard"))

    assignment = conn.execute(
        "SELECT 1 FROM teacher_assignments WHERE school_id = ? AND class_name = ? AND subject = ? AND teacher_code = ?",
        (session["school_id"], grade, subject, teacher_code),
    ).fetchone()
    if not assignment:
        conn.close()
        session.pop('_flashes', None)
        flash("You are not assigned to this class and subject.", "danger")
        return redirect(url_for("select_cba_subject", grade=grade))

    term_rows = conn.execute(
        "SELECT term FROM cba_term_task_configs WHERE school_id = ? AND grade = ? AND subject = ? ORDER BY updated_at DESC",
        (session["school_id"], grade, subject),
    ).fetchall()
    terms = list(dict.fromkeys(row["term"] for row in term_rows))
    if not terms:
        conn.close()
        session.pop('_flashes', None)
        flash("CBA tasks have not been published for this subject.", "warning")
        return redirect(url_for("select_cba_subject", grade=grade))

    term = request.args.get("term", "").strip() or terms[0]
    if term not in terms:
        conn.close()
        session.pop('_flashes', None)
        flash("Select a term with published CBA tasks.", "warning")
        return redirect(
            url_for("enter_cba_marks", grade=grade, subject=subject, term=terms[0])
        )

    config = conn.execute(
        "SELECT tasks_json FROM cba_term_task_configs WHERE school_id = ? AND grade = ? AND subject = ? AND term = ?",
        (session["school_id"], grade, subject, term),
    ).fetchone()
    if not config:
        conn.close()
        session.pop('_flashes', None)
        flash("CBA tasks have not been published for this subject.", "warning")
        return redirect(url_for("select_cba_subject", grade=grade))
    try:
        tasks = validate_tasks(json.loads(config["tasks_json"]))
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        conn.close()
        logging.exception("Invalid CBA task configuration")
        session.pop('_flashes', None)
        flash(f"The CBA task configuration is invalid: {error}", "danger")
        return redirect(url_for("dashboard"))

    students = conn.execute(
        "SELECT id, adm_no, student_name, gender, assessment_number FROM students WHERE school_id = ? AND grade = ? ORDER BY student_name",
        (session["school_id"], grade),
    ).fetchall()

    if request.method == "POST":
        score_rows = []
        try:
            for student in students:
                for task_index, task in enumerate(tasks):
                    raw_score = request.form.get(
                        f"score_{student['id']}_{task_index}", ""
                    )
                    raw_score = (raw_score or "").strip()
                    # A blank task field means the learner was absent, not that
                    # the mark should be omitted from the saved result.
                    if not raw_score:
                        raw_score = "AB"
                    if raw_score.upper() in {"A", "AB"}:
                        raw_score = "AB"
                    convert_raw_score(task, raw_score)
                    score_rows.append(
                        (
                            session["school_id"],
                            grade,
                            subject,
                            term,
                            student["adm_no"],
                            student["student_name"],
                            task["name"],
                            "AB" if raw_score.upper() == "AB" else int(raw_score),
                            teacher_code,
                            datetime.now(timezone.utc).isoformat(),
                        )
                    )
        except ValueError as error:
            conn.close()
            session.pop('_flashes', None)
            flash(str(error), "danger")
            return redirect(url_for("enter_cba_marks", grade=grade, subject=subject))

        conn.execute(
            "DELETE FROM cba_term_scores WHERE school_id = ? AND grade = ? AND subject = ? AND term = ?",
            (session["school_id"], grade, subject, term),
        )
        conn.executemany(
            """
            INSERT INTO cba_term_scores
                (school_id, grade, subject, term, adm_no, student_name, task_name, raw_score, teacher_code, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            score_rows,
        )
        conn.commit()
        conn.close()
        session.pop('_flashes', None)
        flash(f"CBA raw scores for {subject} saved successfully.", "success")
        return redirect(
            url_for("enter_cba_marks", grade=grade, subject=subject, term=term)
        )

    saved_rows = conn.execute(
        "SELECT adm_no, task_name, raw_score FROM cba_term_scores WHERE school_id = ? AND grade = ? AND subject = ? AND term = ?",
        (session["school_id"], grade, subject, term),
    ).fetchall()
    conn.close()
    saved_scores = {}
    for row in saved_rows:
        saved_scores.setdefault(row["adm_no"], {})[row["task_name"]] = row["raw_score"]

    task_bounds = {task["name"]: task_score_bounds(task) for task in tasks}
    return render_template(
        "cloud_cba_marks.html",
        grade=grade,
        subject=subject,
        term=term,
        terms=terms,
        absence_mark=absence_mark_for_grade(grade),
        students=students,
        tasks=tasks,
        task_bounds=task_bounds,
        describe_criterion=describe_criterion,
        saved_scores=saved_scores,
    )


@app.route("/cba/export/<grade>/<export_format>")
def export_cba_marks(grade, export_format):
    if "school_id" not in session:
        return redirect(url_for("teacher_login"))
    if export_format not in {"xlsx", "pdf"}:
        return "Unsupported export format", 404

    subject = request.args.get("subject", "").strip()
    term = request.args.get("term", "").strip()
    teacher_code = session.get("teacher_code")
    if not subject or not teacher_code:
        return "Subject is required", 400

    conn = get_db()
    assignment = conn.execute(
        "SELECT 1 FROM teacher_assignments WHERE school_id = ? AND class_name = ? AND subject = ? AND teacher_code = ?",
        (session["school_id"], grade, subject, teacher_code),
    ).fetchone()
    term_rows = conn.execute(
        "SELECT term FROM cba_term_task_configs WHERE school_id = ? AND grade = ? AND subject = ? ORDER BY updated_at DESC",
        (session["school_id"], grade, subject),
    ).fetchall()
    terms = list(dict.fromkeys(row["term"] for row in term_rows))
    if not term:
        term = terms[0] if terms else ""
    config = conn.execute(
        "SELECT tasks_json FROM cba_term_task_configs WHERE school_id = ? AND grade = ? AND subject = ? AND term = ?",
        (session["school_id"], grade, subject, term),
    ).fetchone()
    if not assignment or not config:
        conn.close()
        return "No CBA results are available for this assigned subject", 404

    tasks = validate_tasks(json.loads(config["tasks_json"]))
    students = conn.execute(
        "SELECT adm_no, assessment_number, student_name, gender FROM students WHERE school_id = ? AND grade = ? ORDER BY student_name COLLATE NOCASE, adm_no",
        (session["school_id"], grade),
    ).fetchall()
    scores = conn.execute(
        "SELECT adm_no, task_name, raw_score FROM cba_term_scores WHERE school_id = ? AND grade = ? AND subject = ? AND term = ?",
        (session["school_id"], grade, subject, term),
    ).fetchall()
    school = conn.execute(
        "SELECT school_name FROM schools WHERE id = ?", (session["school_id"],)
    ).fetchone()
    conn.close()

    scores_by_student = {}
    for row in scores:
        scores_by_student.setdefault(row["adm_no"], {})[row["task_name"]] = row["raw_score"]

    headers = ["Assessment Number", "Learner's Name", "Gender"]
    headers.extend(task["name"] for task in tasks)
    output_rows = []
    for student in students:
        row = [
            student["assessment_number"] or "",
            student["student_name"],
            student["gender"] or "",
        ]
        for task in tasks:
            raw_score = scores_by_student.get(student["adm_no"], {}).get(task["name"])
            if raw_score is None:
                row.append("")
                continue
            converted = convert_raw_score(task, raw_score)
            if converted["points"] is None:
                row.append(absence_mark_for_grade(grade))
            else:
                row.append(converted["points"])
        output_rows.append(row)

    filename = secure_filename(f"{grade}_{subject}_{term}_cba_results.{export_format}")
    if export_format == "xlsx":
        from io import BytesIO
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "CBA Results"
        report_title = f"{school['school_name'] if school else 'CBA Results'} | {grade} | {subject} | {term}"
        worksheet.append([report_title])
        worksheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        worksheet.append(headers)
        for row in output_rows:
            worksheet.append(row)
        worksheet.freeze_panes = "A3"
        worksheet.auto_filter.ref = f"A2:{get_column_letter(len(headers))}{worksheet.max_row}"
        worksheet.sheet_properties.pageSetUpPr.fitToPage = True
        worksheet.page_setup.orientation = "landscape"
        worksheet.page_setup.paperSize = worksheet.PAPERSIZE_A4
        worksheet.page_setup.fitToWidth = 1
        worksheet.page_setup.fitToHeight = 0
        worksheet.print_title_rows = "2:2"
        thin_green = Side(style="thin", color="B7C9C0")
        for cell in worksheet[1]:
            cell.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="245B4B")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        worksheet.row_dimensions[1].height = 28
        for cell in worksheet[2]:
            cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="245B4B")
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        for row in worksheet.iter_rows(min_row=1, max_row=worksheet.max_row):
            for cell in row:
                cell.border = Border(bottom=thin_green)
                if cell.row > 2:
                    cell.alignment = Alignment(vertical="center", wrap_text=True)
                    if cell.row % 2:
                        cell.fill = PatternFill("solid", fgColor="F0F5F2")
        worksheet.row_dimensions[2].height = 24
        worksheet.column_dimensions["A"].width = 23
        worksheet.column_dimensions["B"].width = 29
        worksheet.column_dimensions["C"].width = 12
        for column_index in range(4, len(headers) + 1):
            worksheet.column_dimensions[get_column_letter(column_index)].width = 14
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    title = Paragraph(
        f"{school['school_name'] if school else 'CBA Results'} - {grade} - {subject} - {term}",
        styles["Title"],
    )
    table_data = [headers] + output_rows
    usable_width = landscape(A4)[0] - 24 * mm
    column_weights = [1.55, 2.4, 0.85] + [1.0] * len(tasks)
    weight_total = sum(column_weights)
    column_widths = [usable_width * weight / weight_total for weight in column_weights]
    table = Table(table_data, colWidths=column_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#245b4b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#aebbb5")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf3ef")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    document.build([title, table])
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


def _curriculum_tree(conn, school_id, grade):
    tree = []
    areas = conn.execute(
        "SELECT id, name FROM cbc_learning_areas WHERE school_id = ? AND grade = ? ORDER BY name",
        (school_id, grade),
    ).fetchall()
    for area in areas:
        strands = conn.execute(
            "SELECT id, name FROM cbc_strands WHERE learning_area_id = ? ORDER BY name",
            (area["id"],),
        ).fetchall()
        area_data = {"name": area["name"], "strands": []}
        for strand in strands:
            sub_strands = conn.execute(
                "SELECT name FROM cbc_sub_strands WHERE strand_id = ? ORDER BY name",
                (strand["id"],),
            ).fetchall()
            area_data["strands"].append(
                {"name": strand["name"], "sub_strands": [row["name"] for row in sub_strands]}
            )
        tree.append(area_data)
    return tree


def _upsert_cbc_curriculum(conn, school_id, grade, areas):
    for area in areas:
        conn.execute(
            "INSERT INTO cbc_learning_areas (school_id, grade, name) VALUES (?, ?, ?) ON CONFLICT(school_id, grade, name) DO NOTHING",
            (school_id, grade, area["name"]),
        )
        area_id = conn.execute(
            "SELECT id FROM cbc_learning_areas WHERE school_id = ? AND grade = ? AND name = ?",
            (school_id, grade, area["name"]),
        ).fetchone()["id"]
        for strand in area["strands"]:
            conn.execute(
                "INSERT INTO cbc_strands (learning_area_id, name) VALUES (?, ?) ON CONFLICT(learning_area_id, name) DO NOTHING",
                (area_id, strand["name"]),
            )
            strand_id = conn.execute(
                "SELECT id FROM cbc_strands WHERE learning_area_id = ? AND name = ?",
                (area_id, strand["name"]),
            ).fetchone()["id"]
            for sub_strand in strand["sub_strands"]:
                conn.execute(
                    "INSERT INTO cbc_sub_strands (strand_id, name) VALUES (?, ?) ON CONFLICT(strand_id, name) DO NOTHING",
                    (strand_id, sub_strand),
                )


@app.route("/cbc/curriculum/<grade>", methods=["GET", "POST"])
def manage_cbc_curriculum(grade):
    if "school_id" not in session:
        return redirect(url_for("teacher_login"))
    if not is_admin():
        return "Administrator access required", 403

    conn = get_db()
    if request.method == "POST":
        try:
            submitted = json.loads(request.form.get("curriculum_json", "[]"))
            areas = validate_curriculum(submitted, grade)
            conn.execute("BEGIN")
            _upsert_cbc_curriculum(conn, session["school_id"], grade, areas)
            conn.commit()
            flash("Curriculum structure saved.", "success")
        except (ValueError, TypeError, json.JSONDecodeError, sqlite3.Error) as error:
            conn.rollback()
            flash(str(error), "danger")

    current = _curriculum_tree(conn, session["school_id"], grade)
    conn.close()
    return render_template(
        "cbc_curriculum.html",
        grade=grade,
        curriculum_json=json.dumps(current, indent=2),
        max_learning_areas=9 if grade in {"Grade 7", "Grade 8", "Grade 9"} else None,
    )


SUBJECT_TO_LEARNING_AREA = {
    "MATH": "Mathematics",
    "MAT": "Mathematics",
    "ENG": "English",
    "KISW": "Kiswahili",
    "INT SCIE": "Integrated Science",
    "PRE-TECH": "Pre-Technical Studies",
    "SST": "Social Studies",
    "AGRI": "Agriculture",
    "C/A": "Creative Arts",
    "CRE": "CRE",
    "IRE": "IRE",
    "HRE": "HRE",
}


def _sync_global_curriculum(conn, school_id, grade):
    """Copy the shared strands for this class into the school's own curriculum tables."""
    rows = conn.execute(
        "SELECT area, strands_json FROM global_curriculum WHERE grade = ?", (grade,)
    ).fetchall()
    for row in rows:
        try:
            strands = [
                {"name": item["name"], "sub_strands": list(item["sub_strands"])}
                for item in json.loads(row["strands_json"])
            ]
        except (TypeError, ValueError, KeyError):
            continue
        _upsert_cbc_curriculum(conn, school_id, grade, [{"name": row["area"], "strands": strands}])
    if rows:
        conn.commit()


def _developer_redirect():
    return redirect(url_for("developer_strands"))


@app.route("/developer/strands", methods=["GET", "POST"])
def developer_strands():
    expected = os.environ.get("DEVELOPER_PASSWORD", "")
    if request.method == "POST" and request.form.get("action") == "login":
        supplied = request.form.get("password", "")
        if expected and hmac.compare_digest(supplied.encode(), expected.encode()):
            session["developer"] = True
        else:
            flash("Incorrect developer password.", "danger")
        return _developer_redirect()
    if not session.get("developer"):
        return render_template("cloud_developer.html", authed=False, configured=bool(expected))
    conn = get_db()
    stored = []
    for row in conn.execute(
        "SELECT id, grade, area, strands_json, updated_at FROM global_curriculum"
    ).fetchall():
        strands = json.loads(row["strands_json"])
        stored.append({
            "id": row["id"], "grade": row["grade"], "area": row["area"],
            "strands": len(strands), "sub_strands": sum(len(item["sub_strands"]) for item in strands),
            "updated_at": row["updated_at"][:10],
        })
    conn.close()
    stored.sort(key=lambda item: (GRADE_OPTIONS.index(item["grade"]) if item["grade"] in GRADE_OPTIONS else 99, item["area"]))
    return render_template(
        "cloud_developer.html", authed=True, configured=True, stored=stored, preview=None,
        grades=GRADE_OPTIONS, areas=sorted(set(SUBJECT_TO_LEARNING_AREA.values())),
    )


@app.route("/developer/strands/preview", methods=["POST"])
def developer_strands_preview():
    if not session.get("developer"):
        return _developer_redirect()
    grade = request.form.get("grade", "").strip()
    area = request.form.get("area", "").strip()
    upload = request.files.get("pdf")
    if grade not in GRADE_OPTIONS or not area or not upload or not upload.filename.lower().endswith(".pdf"):
        flash("Choose a class, a learning area and a PDF file.", "danger")
        return _developer_redirect()
    try:
        from cbc_curriculum_import import extract_curriculum_pdf

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            upload.save(handle)
        try:
            strands = extract_curriculum_pdf(handle.name)
        finally:
            os.remove(handle.name)
        areas = validate_curriculum([{"name": area, "strands": strands}], grade)
    except Exception as error:
        logging.exception("Developer curriculum preview failed")
        flash(f"Could not read strands from this PDF: {error}", "danger")
        return _developer_redirect()
    return render_template(
        "cloud_developer.html", authed=True, configured=True, stored=[], grades=GRADE_OPTIONS,
        areas=[], preview={
            "grade": grade, "area": area, "strands": areas[0]["strands"],
            "json": json.dumps(areas[0]["strands"]),
        },
    )


@app.route("/developer/strands/save", methods=["POST"])
def developer_strands_save():
    if not session.get("developer"):
        return _developer_redirect()
    grade = request.form.get("grade", "").strip()
    area = request.form.get("area", "").strip()
    try:
        if grade not in GRADE_OPTIONS:
            raise ValueError("Choose a valid class.")
        areas = validate_curriculum(
            [{"name": area, "strands": json.loads(request.form.get("strands_json", "[]"))}], grade
        )
    except (TypeError, ValueError) as error:
        flash(str(error), "danger")
        return _developer_redirect()
    conn = get_db()
    conn.execute(
        """
        INSERT INTO global_curriculum (grade, area, strands_json, updated_at) VALUES (?, ?, ?, ?)
        ON CONFLICT(grade, area) DO UPDATE SET
        strands_json = excluded.strands_json, updated_at = excluded.updated_at
        """,
        (grade, area, json.dumps(areas[0]["strands"]), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    flash(f"Saved {area} strands for {grade}. All schools now use them.", "success")
    return _developer_redirect()


@app.route("/developer/strands/delete", methods=["POST"])
def developer_strands_delete():
    if not session.get("developer"):
        return _developer_redirect()
    conn = get_db()
    conn.execute("DELETE FROM global_curriculum WHERE id = ?", (request.form.get("id", ""),))
    conn.commit()
    conn.close()
    flash("Strands removed from the portal.", "success")
    return _developer_redirect()


@app.route("/developer/logout", methods=["POST"])
def developer_logout():
    session.pop("developer", None)
    return redirect(url_for("home"))


def _current_exam_percentages(conn, school_id, grade, subject_codes):
    """Return the most recently updated exam title with scores for these subjects and {adm_no: percent}."""
    rows = conn.execute(
        "SELECT adm_no, exam_title, subject_scores_json, updated_at FROM marks WHERE school_id = ? AND grade = ?",
        (school_id, grade),
    ).fetchall()
    exams = {}
    for row in rows:
        try:
            scores = json.loads(row["subject_scores_json"])
        except (TypeError, ValueError):
            continue
        for code in subject_codes:
            raw = (scores.get(code) or {}).get("score")
            try:
                percent = float(raw)
            except (TypeError, ValueError):
                continue
            exam = exams.setdefault(row["exam_title"], {"updated_at": "", "scores": {}})
            exam["updated_at"] = max(exam["updated_at"], row["updated_at"] or "")
            exam["scores"][row["adm_no"]] = percent
            break
    if not exams:
        return None, {}
    title = max(exams, key=lambda name: exams[name]["updated_at"])
    return title, exams[title]["scores"]


@app.route("/cbc/gradebook/<grade>", methods=["GET", "POST"])
def cbc_rubric_gradebook(grade):
    if "school_id" not in session:
        return redirect(url_for("teacher_login"))
    teacher_code = session.get("teacher_code")
    if not teacher_code:
        return redirect(url_for("teacher_login"))

    conn = get_db()
    school = conn.execute(
        "SELECT portal_open FROM schools WHERE id = ?", (session["school_id"],)
    ).fetchone()
    if not school or school["portal_open"] == 0:
        conn.close()
        return "The teachers portal is currently closed", 403
    assignments = conn.execute(
        "SELECT subject FROM teacher_assignments WHERE school_id = ? AND class_name = ? AND teacher_code = ? ORDER BY subject",
        (session["school_id"], grade, teacher_code),
    ).fetchall()
    assigned_areas = [
        SUBJECT_TO_LEARNING_AREA.get(row["subject"].strip().upper(), row["subject"].strip())
        for row in assignments
    ]
    _sync_global_curriculum(conn, session["school_id"], grade)
    configured_areas = conn.execute(
        "SELECT id, name FROM cbc_learning_areas WHERE school_id = ? AND grade = ? ORDER BY name",
        (session["school_id"], grade),
    ).fetchall()
    available_areas = [area for area in configured_areas if area["name"] in assigned_areas]
    area_name = request.values.get("area", "").strip()
    if not area_name and available_areas:
        area_name = available_areas[0]["name"]
    selected_area = next((area for area in available_areas if area["name"] == area_name), None)
    if not selected_area:
        conn.close()
        return "No configured learning area matches your class assignment", 404

    term = request.values.get("term", "Term 1").strip()
    if term not in {"Term 1", "Term 2", "Term 3"}:
        conn.close()
        return "Invalid term", 400
    assessment_type = "Formative"
    try:
        academic_year = int(request.values.get("academic_year", datetime.now().year))
        if academic_year < 2000 or academic_year > 2200:
            raise ValueError
    except (TypeError, ValueError):
        conn.close()
        return "Invalid academic year", 400

    sub_strands = conn.execute(
        "SELECT ss.id, st.name AS strand_name, ss.name AS sub_strand_name FROM cbc_strands st JOIN cbc_sub_strands ss ON ss.strand_id = st.id WHERE st.learning_area_id = ? ORDER BY st.name, ss.name",
        (selected_area["id"],),
    ).fetchall()
    if not sub_strands:
        conn.close()
        return "This learning area has no configured sub-strands", 400
    strands = conn.execute(
        "SELECT id, name FROM cbc_strands WHERE learning_area_id = ? ORDER BY name",
        (selected_area["id"],),
    ).fetchall()
    try:
        requested_strand_id = int(request.values.get("strand_id", ""))
    except (TypeError, ValueError):
        requested_strand_id = None
    selected_strand = next(
        (strand for strand in strands if strand["id"] == requested_strand_id),
        strands[0],
    )
    selected_strand_sub_strands = [
        item for item in sub_strands if item["strand_name"] == selected_strand["name"]
    ]
    try:
        requested_sub_strand_id = int(request.values.get("sub_strand_id", ""))
    except (TypeError, ValueError):
        requested_sub_strand_id = None
    selected_sub_strand = next(
        (
            item
            for item in selected_strand_sub_strands
            if item["id"] == requested_sub_strand_id
        ),
        selected_strand_sub_strands[0],
    )
    students = conn.execute(
        "SELECT id, adm_no, assessment_number, student_name, gender FROM students WHERE school_id = ? AND grade = ? ORDER BY student_name COLLATE NOCASE",
        (session["school_id"], grade),
    ).fetchall()

    area_subject_codes = [
        row["subject"].strip()
        for row in assignments
        if SUBJECT_TO_LEARNING_AREA.get(row["subject"].strip().upper(), row["subject"].strip()) == area_name
    ]
    current_exam, exam_percentages = _current_exam_percentages(
        conn, session["school_id"], grade, area_subject_codes
    )
    gradebook_redirect = dict(
        grade=grade, area=area_name, term=term, academic_year=academic_year,
        strand_id=selected_strand["id"], sub_strand_id=selected_sub_strand["id"],
    )

    if request.method == "POST" and request.form.get("action") == "autofill":
        covered_ids = set()
        for value in request.form.getlist("covered_sub_strand_ids"):
            try:
                covered_ids.add(int(value))
            except ValueError:
                continue
        covered_ids &= {item["id"] for item in sub_strands}
        if not current_exam:
            flash("No current exam marks were found for this subject.", "warning")
        elif not covered_ids:
            flash("Select at least one sub-strand covered in the exam.", "warning")
        else:
            updated_at = datetime.now(timezone.utc).isoformat()
            filled = 0
            kept = 0
            skipped = 0
            for student in students:
                level = rating_from_percentage(exam_percentages.get(student["adm_no"]))
                try:
                    assessment_number = validate_assessment_number(student["assessment_number"])
                except ValueError:
                    assessment_number = None
                if level is None or assessment_number is None:
                    skipped += 1
                    continue
                for sub_strand_id in covered_ids:
                    cursor = conn.execute(
                        "INSERT INTO cbc_rubric_scores (school_id, grade, assessment_number, academic_year, term, assessment_type, sub_strand_id, rating, teacher_code, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(school_id, grade, assessment_number, academic_year, term, assessment_type, sub_strand_id) DO NOTHING",
                        (session["school_id"], grade, assessment_number, academic_year, term, assessment_type, sub_strand_id, str(level), teacher_code, updated_at),
                    )
                    if cursor.rowcount:
                        filled += 1
                    else:
                        kept += 1
            conn.commit()
            message = f"Filled {filled} level(s) from {current_exam}."
            if kept:
                message += f" {kept} existing level(s) were kept."
            if skipped:
                message += f" {skipped} learner(s) skipped (no score or no Assessment Number)."
            flash(message, "success")
        conn.close()
        return redirect(url_for("cbc_rubric_gradebook", **gradebook_redirect))

    if request.method == "POST":
        assessment_numbers = []
        ratings_to_save = []
        try:
            for student in students:
                assessment_number = validate_assessment_number(student["assessment_number"])
                assessment_numbers.append(assessment_number.casefold())
                raw_rating = request.form.get(
                    f"rating_{student['id']}_{selected_sub_strand['id']}", ""
                ).strip()
                if raw_rating:
                    rating = validate_rubric_rating(raw_rating)
                    ratings_to_save.append(
                        (assessment_number, selected_sub_strand["id"], str(rating))
                    )
            if len(assessment_numbers) != len(set(assessment_numbers)):
                raise ValueError("Assessment Numbers must be unique within this class.")
        except ValueError as error:
            conn.close()
            flash(str(error), "danger")
            return redirect(url_for("cbc_rubric_gradebook", **gradebook_redirect))

        conn.execute(
            "DELETE FROM cbc_rubric_scores WHERE school_id = ? AND grade = ? AND academic_year = ? AND term = ? AND assessment_type = ? AND sub_strand_id = ?",
            (session["school_id"], grade, academic_year, term, assessment_type, selected_sub_strand["id"]),
        )
        updated_at = datetime.now(timezone.utc).isoformat()
        for assessment_number, sub_strand_id, rating in ratings_to_save:
            conn.execute(
                "INSERT INTO cbc_rubric_scores (school_id, grade, assessment_number, academic_year, term, assessment_type, sub_strand_id, rating, teacher_code, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (session["school_id"], grade, assessment_number, academic_year, term, assessment_type, sub_strand_id, rating, teacher_code, updated_at),
            )
        conn.commit()
        conn.close()
        flash("Competency ratings saved.", "success")
        return redirect(url_for("cbc_rubric_gradebook", **gradebook_redirect))

    saved = conn.execute(
        "SELECT assessment_number, rating FROM cbc_rubric_scores WHERE school_id = ? AND grade = ? AND academic_year = ? AND term = ? AND assessment_type = ? AND sub_strand_id = ?",
        (session["school_id"], grade, academic_year, term, assessment_type, selected_sub_strand["id"]),
    ).fetchall()
    rating_map = {row["assessment_number"]: row["rating"] for row in saved}
    covered_ids = {
        row["sub_strand_id"]
        for row in conn.execute(
            "SELECT DISTINCT sub_strand_id FROM cbc_rubric_scores WHERE school_id = ? AND grade = ? AND academic_year = ? AND term = ? AND assessment_type = ?",
            (session["school_id"], grade, academic_year, term, assessment_type),
        ).fetchall()
    }
    strand_progress = []
    for strand in strands:
        items = [
            {"id": item["id"], "name": item["sub_strand_name"], "covered": item["id"] in covered_ids}
            for item in sub_strands
            if item["strand_name"] == strand["name"]
        ]
        strand_progress.append({
            "id": strand["id"],
            "name": strand["name"],
            "sub_strands": items,
            "covered_count": sum(item["covered"] for item in items),
        })
    conn.close()
    return render_template(
        "cbc_gradebook.html",
        grade=grade,
        area=area_name,
        areas=available_areas,
        term=term,
        academic_year=academic_year,
        students=students,
        sub_strands=sub_strands,
        strands=strands,
        selected_strand=selected_strand,
        selected_sub_strand=selected_sub_strand,
        selected_strand_sub_strands=selected_strand_sub_strands,
        rating_map=rating_map,
        strand_progress=strand_progress,
        covered_ids=covered_ids,
        current_exam=current_exam,
    )


@app.route("/cbc/profile/<grade>/<assessment_number>")
def cbc_progress_profile(grade, assessment_number):
    if "school_id" not in session:
        return redirect(url_for("teacher_login"))
    teacher_code = session.get("teacher_code")
    if not teacher_code and not is_admin():
        return redirect(url_for("teacher_login"))
    try:
        assessment_number = validate_assessment_number(assessment_number)
    except ValueError as error:
        return str(error), 400

    term = request.args.get("term", "Term 1").strip()
    try:
        academic_year = int(request.args.get("academic_year", datetime.now().year))
    except (TypeError, ValueError):
        return "Invalid academic year", 400
    conn = get_db()
    if teacher_code and not is_admin():
        assignment = conn.execute(
            "SELECT 1 FROM teacher_assignments WHERE school_id = ? AND class_name = ? AND teacher_code = ? LIMIT 1",
            (session["school_id"], grade, teacher_code),
        ).fetchone()
        if not assignment:
            conn.close()
            return "You are not assigned to this class", 403
    learner = conn.execute(
        "SELECT student_name, gender, assessment_number FROM students WHERE school_id = ? AND grade = ? AND assessment_number = ?",
        (session["school_id"], grade, assessment_number),
    ).fetchone()
    if not learner:
        conn.close()
        return "Learner not found", 404
    if conn.execute(
        "SELECT COUNT(*) FROM students WHERE school_id = ? AND assessment_number = ?",
        (session["school_id"], assessment_number),
    ).fetchone()[0] != 1:
        conn.close()
        return "Assessment Number is not unique in this school", 409
    school = conn.execute(
        "SELECT school_name FROM schools WHERE id = ?", (session["school_id"],)
    ).fetchone()
    rows = conn.execute(
        "SELECT la.name AS learning_area, st.name AS strand, ss.name AS sub_strand, rs.assessment_type, rs.rating FROM cbc_rubric_scores rs JOIN cbc_sub_strands ss ON ss.id = rs.sub_strand_id JOIN cbc_strands st ON st.id = ss.strand_id JOIN cbc_learning_areas la ON la.id = st.learning_area_id WHERE rs.school_id = ? AND rs.grade = ? AND rs.assessment_number = ? AND rs.academic_year = ? AND rs.term = ? ORDER BY la.name, st.name, ss.name",
        (session["school_id"], grade, assessment_number, academic_year, term),
    ).fetchall()
    conn.close()

    grouped = {}
    for row in rows:
        area = grouped.setdefault(row["learning_area"], {})
        strand = area.setdefault(row["strand"], {})
        item = strand.setdefault(row["sub_strand"], {"Formative": None})
        item[row["assessment_type"]] = row["rating"]
    profile_areas = []
    for area_name, strands in grouped.items():
        area_formative = []
        profile_strands = []
        for strand_name, sub_strands in strands.items():
            profile_sub_strands = []
            for sub_name, ratings in sub_strands.items():
                if ratings["Formative"] is not None:
                    area_formative.append(ratings["Formative"])
                profile_sub_strands.append({
                    "name": sub_name,
                    "formative": ratings["Formative"],
                })
            profile_strands.append({"name": strand_name, "sub_strands": profile_sub_strands})
        profile_areas.append({
            "name": area_name,
            "strands": profile_strands,
            "descriptor": aggregate_competency(area_formative),
        })
    return render_template(
        "cbc_profile.html",
        school_name=school["school_name"] if school else "",
        learner=learner,
        grade=grade,
        term=term,
        academic_year=academic_year,
        areas=profile_areas,
        rubric_descriptors=RUBRIC_DESCRIPTORS,
        reporting_bands_for_rating=reporting_bands_for_rating,
    )


@app.route("/api/cbc/milestone-results", methods=["POST"])
def save_cbc_milestone_result():
    if "school_id" not in session:
        return jsonify({"success": False, "message": "Login required."}), 401
    if not is_admin():
        return jsonify({"success": False, "message": "Administrator access required."}), 403
    data = request.get_json(silent=True) or {}
    grade = str(data.get("grade", "")).strip()
    try:
        assessment_number = validate_assessment_number(data.get("assessment_number"))
        academic_year = int(data.get("academic_year"))
        national_percent = float(data.get("national_percent"))
        if grade == "Grade 6":
            sba_percent = float(data.get("sba_percent"))
            grade7_sba_percent = None
            grade8_sba_percent = None
        else:
            grade7_sba_percent = float(data.get("grade7_sba_percent"))
            grade8_sba_percent = float(data.get("grade8_sba_percent"))
            sba_percent = (grade7_sba_percent + grade8_sba_percent) / 2
        weighted_result = calculate_milestone_result(
            grade,
            national_percent,
            sba_percent=sba_percent,
            grade7_sba_percent=grade7_sba_percent,
            grade8_sba_percent=grade8_sba_percent,
        )
    except (TypeError, ValueError) as error:
        return jsonify({"success": False, "message": str(error)}), 400

    conn = get_db()
    enrolled = conn.execute(
        "SELECT 1 FROM students WHERE school_id = ? AND grade = ? AND assessment_number = ?",
        (session["school_id"], grade, assessment_number),
    ).fetchone()
    if not enrolled:
        conn.close()
        return jsonify({"success": False, "message": "Learner is not enrolled in this school and milestone grade."}), 404
    conn.execute(
        "INSERT INTO cbc_milestone_results (school_id, grade, assessment_number, academic_year, sba_percent, grade7_sba_percent, grade8_sba_percent, national_percent, weighted_result, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(school_id, grade, assessment_number, academic_year) DO UPDATE SET sba_percent = excluded.sba_percent, grade7_sba_percent = excluded.grade7_sba_percent, grade8_sba_percent = excluded.grade8_sba_percent, national_percent = excluded.national_percent, weighted_result = excluded.weighted_result, updated_at = excluded.updated_at",
        (session["school_id"], grade, assessment_number, academic_year, sba_percent, grade7_sba_percent, grade8_sba_percent, national_percent, weighted_result, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "weighted_result": weighted_result})


def _get_cba_staging_data(grade):
    if "school_id" not in session:
        return None, redirect(url_for("teacher_login"))
    subject = request.args.get("subject", "").strip()
    term = request.args.get("term", "").strip()
    teacher_code = session.get("teacher_code")
    if not subject or not teacher_code:
        return None, ("Subject and teacher assignment are required", 400)

    conn = get_db()
    assignment = conn.execute(
        "SELECT 1 FROM teacher_assignments WHERE school_id = ? AND class_name = ? AND subject = ? AND teacher_code = ?",
        (session["school_id"], grade, subject, teacher_code),
    ).fetchone()
    if not assignment:
        conn.close()
        return None, ("You are not assigned to this class and subject", 403)
    if not term:
        latest = conn.execute(
            "SELECT term FROM cba_term_task_configs WHERE school_id = ? AND grade = ? AND subject = ? ORDER BY updated_at DESC LIMIT 1",
            (session["school_id"], grade, subject),
        ).fetchone()
        term = latest["term"] if latest else ""
    config = conn.execute(
        "SELECT tasks_json FROM cba_term_task_configs WHERE school_id = ? AND grade = ? AND subject = ? AND term = ?",
        (session["school_id"], grade, subject, term),
    ).fetchone()
    if not config:
        conn.close()
        return None, ("No CBA task configuration exists for this term", 404)
    tasks = validate_tasks(json.loads(config["tasks_json"]))
    students = conn.execute(
        "SELECT adm_no, assessment_number, student_name, gender FROM students WHERE school_id = ? AND grade = ? ORDER BY assessment_number COLLATE NOCASE, student_name COLLATE NOCASE",
        (session["school_id"], grade),
    ).fetchall()
    scores = conn.execute(
        "SELECT adm_no, task_name, raw_score FROM cba_term_scores WHERE school_id = ? AND grade = ? AND subject = ? AND term = ?",
        (session["school_id"], grade, subject, term),
    ).fetchall()
    conn.close()
    missing = []
    assessment_counts = {}
    for student in students:
        try:
            assessment_number = validate_assessment_number(student["assessment_number"])
            assessment_counts[assessment_number.casefold()] = assessment_counts.get(assessment_number.casefold(), 0) + 1
        except ValueError:
            missing.append(student["student_name"])
    duplicate_numbers = {
        number for number, count in assessment_counts.items() if count > 1
    }
    if duplicate_numbers:
        for student in students:
            assessment_number = str(student["assessment_number"] or "").strip().casefold()
            if assessment_number in duplicate_numbers:
                missing.append(f"{student['student_name']} (duplicate Assessment Number)")
    # Level tasks report levels 4-1; max-score tasks report the raw score.
    tasks_by_name = {task["name"]: task for task in tasks}
    scores_by_student = {}
    for row in scores:
        task = tasks_by_name.get(row["task_name"])
        if task is None:
            continue
        converted = convert_raw_score(task, row["raw_score"])
        reported = (
            absence_mark_for_grade(grade)
            if converted["points"] is None
            else converted["points"]
        )
        scores_by_student.setdefault(row["adm_no"], {})[row["task_name"]] = reported
    return {
        "grade": grade,
        "subject": subject,
        "term": term,
        "tasks": tasks,
        "students": students,
        "missing": missing,
        "scores_by_student": scores_by_student,
    }, None


@app.route("/cba/staging/<grade>")
def cba_staging_area(grade):
    context, error = _get_cba_staging_data(grade)
    if error:
        return error
    return render_template("cbc_staging.html", **context)


@app.route("/cba/staging/<grade>/download")
def download_cba_staging_csv(grade):
    context, error = _get_cba_staging_data(grade)
    if error:
        return error
    if context.get("missing"):
        return jsonify({"success": False, "missing_assessment_numbers": context["missing"]}), 400
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Assessment Number", "Learner's Name", "Gender", *[task["name"] for task in context["tasks"]]])
    for student in context["students"]:
        try:
            assessment_number = validate_assessment_number(student["assessment_number"])
        except ValueError:
            return jsonify({"success": False, "message": "A learner is missing a valid Assessment Number."}), 400
        student_scores = context["scores_by_student"].get(student["adm_no"], {})
        writer.writerow([
            assessment_number,
            student["student_name"],
            student["gender"] or "",
            *[student_scores.get(task["name"], "") for task in context["tasks"]],
        ])
    file_buffer = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    filename = secure_filename(f"{grade}_{context['subject']}_{context['term']}_knec_cba.csv")
    return send_file(file_buffer, as_attachment=True, download_name=filename, mimetype="text/csv; charset=utf-8")


@app.route("/api/fetch_cba_results", methods=["POST"])
def api_fetch_cba_results():
    data = request.get_json(silent=True) or {}
    school_code = str(data.get("school_code", "")).strip().lower()
    password = data.get("password", "")
    grade = str(data.get("grade", "")).strip()
    subject = str(data.get("subject", "")).strip()
    term = str(data.get("term", "")).strip()
    if not school_code or not password or not grade or not subject:
        return jsonify({"success": False, "message": "Missing school credentials or class/subject."}), 400

    conn = get_db()
    try:
        school = conn.execute(
            "SELECT id, password_hash FROM schools WHERE school_code = ?",
            (school_code,),
        ).fetchone()
        if not school or not check_password_hash(school["password_hash"], password):
            return jsonify({"success": False, "message": "Invalid school credentials."}), 401

        if not term:
            latest = conn.execute(
                "SELECT term FROM cba_term_task_configs WHERE school_id = ? AND grade = ? AND subject = ? ORDER BY updated_at DESC LIMIT 1",
                (school["id"], grade, subject),
            ).fetchone()
            term = latest["term"] if latest else ""
        config = conn.execute(
            "SELECT tasks_json FROM cba_term_task_configs WHERE school_id = ? AND grade = ? AND subject = ? AND term = ?",
            (school["id"], grade, subject, term),
        ).fetchone()
        if not config:
            return jsonify({"success": False, "message": "No CBA tasks found for this class, subject, and term."}), 404

        tasks = validate_tasks(json.loads(config["tasks_json"]))
        students = conn.execute(
            "SELECT adm_no, assessment_number, student_name, gender FROM students WHERE school_id = ? AND grade = ? ORDER BY assessment_number COLLATE NOCASE, student_name COLLATE NOCASE",
            (school["id"], grade),
        ).fetchall()
        assessment_numbers = []
        for student in students:
            assessment_numbers.append(validate_assessment_number(student["assessment_number"]))
        if len({number.casefold() for number in assessment_numbers}) != len(assessment_numbers):
            return jsonify({"success": False, "message": "Learner Assessment Numbers must be unique."}), 400
        scores = conn.execute(
            "SELECT adm_no, task_name, raw_score FROM cba_term_scores WHERE school_id = ? AND grade = ? AND subject = ? AND term = ?",
            (school["id"], grade, subject, term),
        ).fetchall()

        scores_by_student = {}
        for row in scores:
            scores_by_student.setdefault(row["adm_no"], {})[row["task_name"]] = row["raw_score"]

        columns = ["Assessment Number", "Learner's Name", "Gender"]
        columns.extend(task["name"] for task in tasks)
        absence_mark = absence_mark_for_grade(grade)
        records = []
        for student, assessment_number in zip(students, assessment_numbers):
            row = [
                assessment_number,
                student["student_name"],
                student["gender"] or "",
            ]
            for task in tasks:
                raw_score = scores_by_student.get(student["adm_no"], {}).get(task["name"])
                if raw_score is None:
                    row.append("")
                    continue
                converted = convert_raw_score(task, raw_score)
                if converted["points"] is None:
                    row.append(absence_mark)
                else:
                    row.append(converted["points"])
            records.append(row)

        return jsonify(
            {
                "success": True,
                "grade": grade,
                "subject": subject,
                "term": term,
                "columns": columns,
                "records": records,
            }
        )
    except Exception as error:
        logging.exception("Could not fetch converted CBA results")
        return jsonify({"success": False, "message": str(error)}), 500
    finally:
        conn.close()


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
        print(
            f"DEBUG API: Processing record for {r['student_name']}, original scores: {scores}"
        )

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
                            level_points = {
                                "EE1": 8,
                                "EE2": 7,
                                "ME1": 6,
                                "ME2": 5,
                                "AE1": 4,
                                "AE2": 3,
                                "BE1": 2,
                                "BE2": 1,
                            }
                            points = level_points.get(rating, 0)
                        else:
                            rating = get_grade_4_6_rating(score_int)
                            level_points = {
                                "EE1": 8,
                                "EE2": 7,
                                "ME1": 6,
                                "ME2": 5,
                                "AE1": 4,
                                "AE2": 3,
                                "BE1": 2,
                                "BE2": 1,
                            }
                            points = level_points.get(rating, 0)
                        print(
                            f"DEBUG API: Converted old format {subject}: score={score_int} -> rating={rating}, points={points}"
                        )
                    except ValueError:
                        rating = ""
                        points = 0

                # Convert to new dict format
                scores[subject] = {"score": score, "rating": rating, "points": points}
            elif isinstance(data, dict):
                # If rating or points are missing, calculate them
                if (
                    "rating" not in data
                    or "points" not in data
                    or not data.get("rating")
                ):
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
                                level_points = {
                                    "EE1": 8,
                                    "EE2": 7,
                                    "ME1": 6,
                                    "ME2": 5,
                                    "AE1": 4,
                                    "AE2": 3,
                                    "BE1": 2,
                                    "BE2": 1,
                                }
                                points = level_points.get(rating, 0)
                            else:
                                rating = get_grade_4_6_rating(score_int)
                                level_points = {
                                    "EE1": 8,
                                    "EE2": 7,
                                    "ME1": 6,
                                    "ME2": 5,
                                    "AE1": 4,
                                    "AE2": 3,
                                    "BE1": 2,
                                    "BE2": 1,
                                }
                                points = level_points.get(rating, 0)
                            print(
                                f"DEBUG API: Calculated missing {subject}: score={score_int} -> rating={rating}, points={points}"
                            )
                        except ValueError:
                            rating = ""
                            points = 0

                    # Update the data with calculated values
                    data["rating"] = rating
                    data["points"] = points
                    scores[subject] = data

        # Get database values first
        db_total_points = r["total_points"] if r["total_points"] is not None else None
        db_avg_level = r["average_level"] if r["average_level"] is not None else None

        print(
            f"DEBUG API: DB values - total_points={db_total_points}, avg_level={db_avg_level}"
        )

        # Calculate total_points/total_scores
        # For JSS: calculate from points if DB value is None or "0"
        # For non-JSS: always calculate from scores (since DB stores total_points but we need total_scores)
        if is_jss:
            if db_total_points is None or db_total_points == "0":
                total_points = 0
                for subject, data in scores.items():
                    if isinstance(data, dict) and data.get("points"):
                        try:
                            total_points += int(data["points"])
                        except ValueError:
                            pass
                print(
                    f"DEBUG API: Calculated total_points (from points)={total_points} for JSS"
                )
                db_total_points = str(total_points)
            else:
                print(
                    f"DEBUG API: Using database total_points={db_total_points} for JSS"
                )
        else:
            # For non-JSS grades, always calculate from scores since we need total_scores
            # The DB column is total_points but we're sending total_scores field
            total_points = 0
            for subject, data in scores.items():
                if isinstance(data, dict) and data.get("score"):
                    try:
                        total_points += int(data["score"])
                    except ValueError:
                        pass
            print(
                f"DEBUG API: Calculated total_scores (from scores)={total_points} for non-JSS"
            )
            db_total_points = str(total_points)

        # Calculate average level only if database value is missing (None)
        # For previous exams, use database average_level if it exists
        if db_avg_level is None:
            # Calculate average level from total_points
            total_points_int = int(db_total_points) if db_total_points else 0
            # Get number of subjects from the scores JSON
            num_subjects = (
                len(json.loads(row["subject_scores_json"]))
                if row and row.get("subject_scores_json")
                else 9
            )
            if is_jss:
                avg_level = calculate_final_level(
                    total_points_int, is_primary=False, num_subjects=num_subjects
                )
            else:
                avg_level = calculate_final_level(
                    total_points_int, is_primary=True, num_subjects=num_subjects
                )
            db_avg_level = avg_level
            print(
                f"DEBUG API: Calculated avg_level={avg_level} from total_points={total_points_int}"
            )
        else:
            print(f"DEBUG API: Using database average_level={db_avg_level}")

        # Use appropriate field name based on grade level
        # JSS uses total_points (sum of rating points), other grades use total_scores (sum of raw scores)
        # Note: average_level is NOT sent - local system will calculate it dynamically
        if is_jss:
            marks_list.append(
                {
                    "adm_no": r["adm_no"],
                    "student_name": r["student_name"],
                    "grade": r["grade"],
                    "exam_title": r["exam_title"],
                    "scores": scores,
                    "total_points": db_total_points,
                }
            )
        else:
            marks_list.append(
                {
                    "adm_no": r["adm_no"],
                    "student_name": r["student_name"],
                    "grade": r["grade"],
                    "exam_title": r["exam_title"],
                    "scores": scores,
                    "total_scores": db_total_points,
                }
            )

    # Return with the key 'marks'
    return jsonify({"success": True, "marks": marks_list})


@app.route("/api/consume_marks", methods=["POST"])
def api_consume_marks():
    """Kept for older desktop versions; marks now stay until a new exam replaces them."""
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

        return jsonify({"success": True, "message": "Marks kept on the portal"})

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

    logging.info(
        f"Received student report for: {report.get('student_name')}, keys: {list(report.keys())}"
    )
    if "exam_title" in report:
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
        generated_date = report.get(
            "generated_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        logging.info(
            f"Saving report - student_name: {report.get('student_name')}, adm_no: {report.get('adm_no')} (type: {type(report.get('adm_no'))}), grade: {report.get('grade')}, school: {school['school_name']}"
        )

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
                generated_date,
            ),
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
                    (
                        report.get("student_name"),
                        report.get("adm_no"),
                        report.get("grade"),
                    ),
                )
                student_row = student_cursor.fetchone()

                if student_row:
                    student_id = student_row[0]
                    # Get FCM token for this student
                    token_cursor = conn.execute(
                        "SELECT token FROM fcm_tokens WHERE student_id = ?",
                        (student_id,),
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
                                "adm_no": report.get("adm_no"),
                            },
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

        logging.info(
            f"Received FCM token registration - student_id: {student_id}, token: {token[:20] if token else None}..., device: {device_info[:50] if device_info else None}..."
        )
        logging.info(f"Request IP: {request.remote_addr}")
        logging.info(
            f"User-Agent: {request.headers.get('User-Agent', 'Unknown')[:100]}"
        )

        if not student_id or not token:
            logging.warning(
                "FCM token registration failed: Missing student_id or token"
            )
            return (
                jsonify({"success": False, "message": "Missing student_id or token"}),
                400,
            )

        conn = get_db()
        try:
            # Insert or update the token
            conn.execute(
                """
                INSERT OR REPLACE INTO fcm_tokens (student_id, token, device_info, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (student_id, token, device_info),
            )

            conn.commit()
            logging.info(
                f"✓ FCM token registered successfully for student_id={student_id}"
            )
            return jsonify(
                {"success": True, "message": "Token registered successfully"}
            )

        except Exception as e:
            logging.error(f"Error registering FCM token in database: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()

    except Exception as e:
        logging.error(f"FCM token registration error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/log_fcm_click", methods=["POST"])
def api_log_fcm_click():
    """Log FCM button clicks for debugging"""
    logging.info("=== FCM Button Clicked ===")
    data = request.json
    action = data.get("action", "unknown")
    logging.info(f"FCM button action: {action}")
    logging.info(f"Request IP: {request.remote_addr}")
    return jsonify({"success": True})


@app.route("/parent/enable_notifications", methods=["GET", "POST"])
def parent_enable_notifications():
    """Server-side FCM registration page (works without JavaScript)"""
    logging.info("=== Server-side FCM Registration Page Accessed ===")

    # If already logged in, show registration page
    if "parent_student_id" in session:
        student_id = session.get("parent_student_id")
        return render_template("fcm_registration.html", student_id=student_id)

    # If POST with login credentials, authenticate first
    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        school_name = request.form.get("school_name", "").strip()
        adm_no = request.form.get("adm_no", "").strip()

        if not student_name or not school_name or not adm_no:
            return render_template(
                "fcm_registration_login.html", error="Please fill in all fields"
            )

        # Authenticate
        conn = get_db()
        try:
            student_name_normalized = student_name.lower().strip()
            school_name_normalized = school_name.lower().strip()
            adm_no_normalized = adm_no.strip()

            student = conn.execute(
                """
                SELECT s.id, s.school_id, s.grade, sc.school_name
                FROM students s
                JOIN schools sc ON s.school_id = sc.id
                WHERE LOWER(s.student_name) = ? AND LOWER(sc.school_name) = ? AND s.adm_no = ?
                """,
                (student_name_normalized, school_name_normalized, adm_no_normalized),
            ).fetchone()

            if student:
                session["parent_student_id"] = student["id"]
                session["parent_student_name"] = student_name
                session["parent_school_name"] = school_name
                session["parent_adm_no"] = adm_no
                session["parent_grade"] = student["grade"]
                return render_template(
                    "fcm_registration.html", student_id=student["id"]
                )
            else:
                return render_template(
                    "fcm_registration_login.html",
                    error="Student not found. Please check your details.",
                )
        except Exception as e:
            logging.error(f"Parent login error: {e}")
            return render_template(
                "fcm_registration_login.html",
                error="An error occurred. Please try again.",
            )
        finally:
            conn.close()

    # Show login form
    return render_template("fcm_registration_login.html")


@app.route("/api/save_newsletter", methods=["POST"])
def api_save_newsletter():
    """Save a newsletter to the cloud database"""
    data = request.get_json(silent=True) or request.form
    school_code = data.get("school_code", "").strip().lower()
    username = data.get("username", "")
    password = data.get("password", "")
    newsletter_data = data.get("newsletter", {})

    if isinstance(newsletter_data, str):
        try:
            newsletter_data = json.loads(newsletter_data)
        except json.JSONDecodeError:
            return jsonify({"success": False, "message": "Invalid newsletter data"}), 400

    logging.info(
        f"Received newsletter: {newsletter_data.get('subject')}, target: {newsletter_data.get('target_type')}"
    )

    if not school_code or not newsletter_data:
        return jsonify({"success": False, "message": "Missing required data"}), 400

    conn = get_db()
    try:
        # Verify school
        school = conn.execute(
            "SELECT id, school_name FROM schools WHERE school_code = ?", (school_code,)
        ).fetchone()
        if not school:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "School not found. Please check your school code.",
                    }
                ),
                404,
            )

        attachment = request.files.get("attachment")
        if attachment and attachment.filename:
            safe_filename = secure_filename(attachment.filename)
            extension = os.path.splitext(safe_filename)[1].lower()
            if not safe_filename or extension not in {".pdf", ".png", ".jpg", ".jpeg", ".gif"}:
                return jsonify({"success": False, "message": "Unsupported attachment type"}), 400

            safe_school_code = secure_filename(school_code)
            upload_dir = os.path.join(
                PROJECT_DIR, "static", "uploads", "newsletters", safe_school_code
            )
            os.makedirs(upload_dir, exist_ok=True)
            stored_filename = f"{uuid.uuid4().hex}_{safe_filename}"
            attachment.save(os.path.join(upload_dir, stored_filename))
            newsletter_data["attachment_path"] = url_for(
                "newsletter_attachment",
                school_code=safe_school_code,
                filename=stored_filename,
            )

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

            if "title" in columns and "subject" not in columns:
                logging.info(
                    "Migrating newsletters table from old schema to new schema"
                )
                conn.execute("ALTER TABLE newsletters ADD COLUMN subject TEXT")
                conn.execute("ALTER TABLE newsletters ADD COLUMN body TEXT")
                conn.execute("ALTER TABLE newsletters ADD COLUMN target_type TEXT")
                conn.execute("ALTER TABLE newsletters ADD COLUMN class_context TEXT")
                conn.execute("ALTER TABLE newsletters ADD COLUMN recipient_role TEXT")
                conn.execute(
                    "ALTER TABLE newsletters ADD COLUMN send_email INTEGER DEFAULT 0"
                )
                conn.execute(
                    "ALTER TABLE newsletters ADD COLUMN send_sms INTEGER DEFAULT 0"
                )
                conn.execute(
                    "ALTER TABLE newsletters ADD COLUMN is_draft INTEGER DEFAULT 1"
                )
                conn.execute("ALTER TABLE newsletters ADD COLUMN sent_at TIMESTAMP")

                # Copy data from old columns to new columns
                conn.execute(
                    "UPDATE newsletters SET subject = title WHERE subject IS NULL"
                )
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

            if "title" in columns and "subject" not in columns:
                logging.info(
                    "Migrating portal_announcements table from old schema to new schema"
                )
                conn.execute("ALTER TABLE portal_announcements ADD COLUMN subject TEXT")
                conn.execute("ALTER TABLE portal_announcements ADD COLUMN body TEXT")
                conn.execute(
                    "ALTER TABLE portal_announcements ADD COLUMN target_type TEXT"
                )
                conn.execute(
                    "ALTER TABLE portal_announcements ADD COLUMN recipient_role TEXT"
                )
                conn.execute(
                    "ALTER TABLE portal_announcements ADD COLUMN attachment_path TEXT"
                )

                # Copy data from old columns to new columns
                conn.execute(
                    "UPDATE portal_announcements SET subject = title WHERE subject IS NULL"
                )
                conn.execute(
                    "UPDATE portal_announcements SET body = content WHERE body IS NULL"
                )

                conn.commit()
                logging.info("Portal_announcements table migration completed")
            elif "attachment_path" not in columns:
                # Add attachment_path if missing but other columns exist
                logging.info(
                    "Adding attachment_path column to portal_announcements table"
                )
                conn.execute(
                    "ALTER TABLE portal_announcements ADD COLUMN attachment_path TEXT"
                )
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

        if "title" in columns:
            # Old schema - use title and content columns
            cursor = conn.execute(
                """
                INSERT INTO newsletters (
                    title, content, target_type, class_context, recipient_role,
                    attachment_path, send_email, send_sms, is_draft, sent_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    newsletter_data.get("subject"),
                    newsletter_data.get("body"),
                    newsletter_data.get("target_type"),
                    newsletter_data.get("class_context"),
                    newsletter_data.get("recipient_role"),
                    newsletter_data.get("attachment_path"),
                    newsletter_data.get("send_email", 0),
                    newsletter_data.get("send_sms", 0),
                    0,  # is_draft = 0 (published)
                    "CURRENT_TIMESTAMP",
                ),
            )
        else:
            # New schema - use subject and body columns
            cursor = conn.execute(
                """
                INSERT INTO newsletters (
                    subject, body, target_type, class_context, recipient_role,
                    attachment_path, send_email, send_sms, is_draft, sent_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    newsletter_data.get("subject"),
                    newsletter_data.get("body"),
                    newsletter_data.get("target_type"),
                    newsletter_data.get("class_context"),
                    newsletter_data.get("recipient_role"),
                    newsletter_data.get("attachment_path"),
                    newsletter_data.get("send_email", 0),
                    newsletter_data.get("send_sms", 0),
                    0,  # is_draft = 0 (published)
                    "CURRENT_TIMESTAMP",
                ),
            )

        newsletter_id = cursor.lastrowid

        # Insert into portal_announcements table (handle both old and new schemas)
        cursor = conn.execute("PRAGMA table_info(portal_announcements)")
        columns_info = cursor.fetchall()
        columns = {row[1]: row[2] for row in columns_info}  # column name: type

        # Log column order for debugging
        logging.info(
            f"Portal announcements columns: {[row[1] for row in columns_info]}"
        )

        if "title" in columns:
            # Old schema - use title and content columns
            # Check if it's the really old schema with published_at in position 4
            if len(columns_info) <= 5:
                # Very old schema: id, newsletter_id, title, content, published_at
                # class_context might not exist or be in wrong position
                logging.info("Using very old schema INSERT")
                cursor = conn.execute(
                    """
                    INSERT INTO portal_announcements (
                        newsletter_id, title, content, published_at
                    ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        newsletter_id,
                        newsletter_data.get("subject"),
                        newsletter_data.get("body"),
                    ),
                )
                # Try to add class_context if column exists
                if "class_context" in columns:
                    announcement_id = cursor.lastrowid
                    conn.execute(
                        "UPDATE portal_announcements SET class_context = ? WHERE id = ?",
                        (newsletter_data.get("class_context"), announcement_id),
                    )
            elif "attachment_path" in columns and "target_type" in columns:
                # Migrated old schema with new columns - use positional INSERT to avoid column name issues
                logging.info("Using migrated old schema INSERT with positional values")
                # Column order: id, newsletter_id, title, content, class_context, published_at, subject, body, target_type, recipient_role, attachment_path
                cursor = conn.execute(
                    """
                    INSERT INTO portal_announcements 
                    (newsletter_id, title, content, class_context, published_at, subject, body, target_type, recipient_role, attachment_path)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
                """,
                    (
                        newsletter_id,
                        newsletter_data.get("subject"),
                        newsletter_data.get("body"),
                        newsletter_data.get("class_context"),
                        newsletter_data.get("subject"),  # subject (new column)
                        newsletter_data.get("body"),  # body (new column)
                        newsletter_data.get("target_type"),
                        newsletter_data.get("recipient_role"),
                        newsletter_data.get("attachment_path"),
                    ),
                )
            else:
                # Pure old schema without new columns
                logging.info("Using pure old schema INSERT")
                cursor = conn.execute(
                    """
                    INSERT INTO portal_announcements (
                        newsletter_id, title, content, class_context, published_at
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        newsletter_id,
                        newsletter_data.get("subject"),
                        newsletter_data.get("body"),
                        newsletter_data.get("class_context"),
                    ),
                )
        else:
            # New schema - use subject and body columns
            logging.info("Using new schema INSERT")
            if "attachment_path" in columns:
                cursor = conn.execute(
                    """
                    INSERT INTO portal_announcements (
                        newsletter_id, subject, body, target_type, 
                        class_context, recipient_role, attachment_path, published_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        newsletter_id,
                        newsletter_data.get("subject"),
                        newsletter_data.get("body"),
                        newsletter_data.get("target_type"),
                        newsletter_data.get("class_context"),
                        newsletter_data.get("recipient_role"),
                        newsletter_data.get("attachment_path"),
                    ),
                )
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO portal_announcements (
                        newsletter_id, subject, body, target_type, 
                        class_context, recipient_role, published_at
                    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        newsletter_id,
                        newsletter_data.get("subject"),
                        newsletter_data.get("body"),
                        newsletter_data.get("target_type"),
                        newsletter_data.get("class_context"),
                        newsletter_data.get("recipient_role"),
                    ),
                )

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
                (recipient_role, class_context),
            )
            student_row = cursor.fetchone()
            if student_row:
                student_ids = [student_row[0]]
        elif target_type == "By Stream":
            # Get students in specific stream
            cursor = conn.execute(
                "SELECT id FROM students WHERE grade = ? AND stream = ?",
                (class_context, recipient_role),
            )
            student_ids = [row[0] for row in cursor.fetchall()]
        elif class_context == "All Classes" or target_type == "All School":
            # Get all students
            cursor = conn.execute("SELECT id FROM students")
            student_ids = [row[0] for row in cursor.fetchall()]
        else:
            # Get students in specific class
            cursor = conn.execute(
                "SELECT id FROM students WHERE grade = ?", (class_context,)
            )
            student_ids = [row[0] for row in cursor.fetchall()]

        # Create notification entries
        for student_id in student_ids:
            conn.execute(
                """
                INSERT OR IGNORE INTO parent_view_status (student_id, content_type, content_id, has_viewed)
                VALUES (?, ?, ?, 0)
            """,
                (student_id, "newsletter", announcement_id),
            )

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
                logging.info(
                    f"Deleted {deleted_count} old newsletters, keeping only 3 latest"
                )
            conn.commit()
        except Exception as e:
            logging.error(f"Error deleting old newsletters: {e}")

        # Send FCM notifications
        try:
            from fcm_service import get_fcm_service

            fcm_service = get_fcm_service()

            logging.info(f"=== FCM Service Check ===")
            logging.info(f"FCM service available: {fcm_service.is_available()}")
            logging.info(f"Target student_ids: {student_ids}")

            if fcm_service.is_available():
                # Get FCM tokens for target students
                tokens = []
                for student_id in student_ids:
                    cursor = conn.execute(
                        "SELECT token FROM fcm_tokens WHERE student_id = ?",
                        (student_id,),
                    )
                    token_row = cursor.fetchone()
                    if token_row:
                        tokens.append(token_row[0])
                        logging.info(f"Found FCM token for student_id={student_id}")
                    else:
                        logging.info(f"No FCM token found for student_id={student_id}")

                logging.info(f"Total FCM tokens found: {len(tokens)}")

                if tokens:
                    # Send multicast notification
                    result = fcm_service.send_multicast_notification(
                        tokens=tokens,
                        title=f"New Newsletter: {newsletter_data.get('subject')}",
                        body="A new newsletter has been published. Check your portal.",
                        data={
                            "type": "newsletter",
                            "announcement_id": str(announcement_id),
                            "subject": newsletter_data.get("subject"),
                        },
                    )
                    logging.info(f"FCM notifications sent: {result}")
                else:
                    logging.info("No FCM tokens found for target students")
            else:
                logging.info("FCM service not available, skipping push notifications")

        except Exception as e:
            logging.error(f"Error sending FCM notifications: {e}")

        logging.info(
            f"Newsletter synced to cloud: {newsletter_data.get('subject')}, {len(student_ids)} notifications created"
        )
        return jsonify(
            {
                "success": True,
                "message": f"Newsletter saved successfully, {len(student_ids)} notifications created",
            }
        )

    except Exception as e:
        logging.error(f"Save newsletter error: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/newsletter-attachments/<school_code>/<filename>")
def newsletter_attachment(school_code, filename):
    """Serve a newsletter attachment inline or as a downloadable file."""
    safe_school_code = secure_filename(school_code)
    safe_filename = secure_filename(filename)
    if not safe_school_code or safe_filename != filename:
        return jsonify({"success": False, "message": "Attachment not found"}), 404

    upload_dir = os.path.join(
        PROJECT_DIR, "static", "uploads", "newsletters", safe_school_code
    )
    return send_from_directory(
        upload_dir,
        safe_filename,
        as_attachment=request.args.get("download") == "1",
    )


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
            generated_date = report.get(
                "generated_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

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
                    generated_date,
                ),
            )
            saved_count += 1
        conn.commit()

        return jsonify(
            {"success": True, "message": f"Saved {saved_count} reports successfully"}
        )
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
            (student_name, school_name, adm_no),
        ).fetchone()

        if not report:
            return jsonify({"success": False, "message": "Report not found"}), 404

        import json

        report_data = json.loads(report["report_data"])

        return jsonify(
            {
                "success": True,
                "report": report_data,
                "generated_date": report["generated_date"],
            }
        )
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
            session.pop('_flashes', None)
            flash("Please fill in all fields", "error")
            return render_template("cloud_parent_login.html")

        # Verify student exists (case-insensitive and flexible name matching)
        conn = get_db()
        try:
            # Normalize inputs for flexible matching
            student_name_normalized = student_name.lower().strip()
            school_name_normalized = school_name.lower().strip()
            adm_no_normalized = adm_no.strip()

            student = conn.execute(
                """
                SELECT s.id, s.school_id, s.grade, sc.school_name
                FROM students s
                JOIN schools sc ON s.school_id = sc.id
                WHERE LOWER(s.student_name) = ? AND LOWER(sc.school_name) = ? AND s.adm_no = ?
                """,
                (student_name_normalized, school_name_normalized, adm_no_normalized),
            ).fetchone()

            if student:
                # Check if system is locked and payment is required
                payment_settings = conn.execute(
                    "SELECT * FROM payment_settings ORDER BY id DESC LIMIT 1"
                ).fetchone()
                
                if payment_settings and payment_settings["system_locked"] == 1:
                    # System is locked, check payment status
                    payment_status = conn.execute(
                        """
                        SELECT payment_status, payment_type 
                        FROM student_payments 
                        WHERE adm_no = ? AND payment_status = 'paid'
                        """,
                        (adm_no_normalized,)
                    ).fetchone()
                    
                    if not payment_status:
                        # Student hasn't paid - show warning message
                        session.pop('_flashes', None)
                        flash(
                            "⚠️ PAYMENT REQUIRED: You will not be able to view your child's newsletters and reports "
                            "until the required payment is made. Please contact the school administration for payment details.",
                            "warning"
                        )
                        # Still allow login but with restricted access
                        session["parent_student_id"] = student["id"]
                        session["parent_student_name"] = student_name
                        session["parent_school_name"] = school_name
                        session["parent_adm_no"] = adm_no
                        session["parent_grade"] = student["grade"]
                        session["payment_status"] = "unpaid"
                        return redirect(url_for("parent_dashboard"))
                
                # System not locked or student has paid - normal login
                session["parent_student_id"] = student["id"]
                session["parent_student_name"] = student_name
                session["parent_school_name"] = school_name
                session["parent_adm_no"] = adm_no
                session["parent_grade"] = student["grade"]
                session["payment_status"] = "paid"
                return redirect(url_for("parent_dashboard"))
            else:
                session.pop('_flashes', None)
                flash("Student not found. Please check your details.", "error")
        except Exception as e:
            logging.error(f"Parent login error: {e}")
            session.pop('_flashes', None)
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
        unread_newsletters = conn.execute(
            """
            SELECT COUNT(*) as count FROM parent_view_status
            WHERE student_id = ? AND content_type = 'newsletter' AND has_viewed = 0
        """,
            (student_id,),
        ).fetchone()["count"]

        # Check unread reports (assuming reports have content_type 'report')
        unread_reports = conn.execute(
            """
            SELECT COUNT(*) as count FROM parent_view_status
            WHERE student_id = ? AND content_type = 'report' AND has_viewed = 0
        """,
            (student_id,),
        ).fetchone()["count"]

        return render_template(
            "cloud_parent_landing.html",
            school_name=session.get("parent_school_name"),
            student_name=session.get("parent_student_name"),
            student_grade=session.get("parent_grade"),
            student_adm_no=session.get("parent_adm_no"),
            unread_newsletters=unread_newsletters,
            unread_reports=unread_reports,
        )
    finally:
        conn.close()


@app.route("/parent/report")
def parent_report():
    logging.info(f"Parent report accessed, session keys: {list(session.keys())}")
    if "parent_student_id" not in session:
        logging.warning("Parent report: No parent_student_id in session")
        return redirect(url_for("parent_login"))

    # Check payment status before allowing report access
    if session.get("payment_status") == "unpaid":
        session.pop('_flashes', None)
        flash(
            "⚠️ PAYMENT REQUIRED: You cannot view your child's report until the required payment is made. "
            "Please contact the school administration for payment details.",
            "error"
        )
        return redirect(url_for("parent_dashboard"))

    conn = get_db()
    try:
        # Fetch the student's report
        logging.info(
            f"Fetching report for student: {session.get('parent_student_name')}, school: {session.get('parent_school_name')}, adm_no: {session.get('parent_adm_no')} (type: {type(session.get('parent_adm_no'))})"
        )

        report = conn.execute(
            """
            SELECT report_data, generated_date FROM student_reports
            WHERE LOWER(student_name) = ? AND LOWER(school_name) = ? AND adm_no = ?
            ORDER BY generated_date DESC LIMIT 1
            """,
            (
                session["parent_student_name"].lower(),
                session["parent_school_name"].lower(),
                session["parent_adm_no"],
            ),
        ).fetchone()
        logging.info(f"Report fetch result: {report is not None}")
        if report:
            logging.info(
                f"Report found for {session['parent_student_name']}, generated_date: {report['generated_date']}"
            )
        else:
            logging.warning(
                f"Report NOT found for {session['parent_student_name']} with adm_no: {session['parent_adm_no']}"
            )

        import json

        if report:
            logging.info("Report found, parsing JSON")
            report_data = json.loads(report["report_data"])
            # Log current_marks keys for debugging
            if "current_marks" in report_data:
                logging.info(
                    f"Current marks keys: {list(report_data['current_marks'].keys())[:20]}"
                )
                # Check for int_scie columns
                for key in [
                    "int_scie_s",
                    "int_scie_r",
                    "int_scie_p",
                    "intcie_s",
                    "intcie_r",
                    "intcie_p",
                ]:
                    if key in report_data["current_marks"]:
                        logging.info(
                            f"Found {key} = {report_data['current_marks'][key]}"
                        )
            # Generate analytics data
            logging.info("Generating analytics")
            report_data = generate_analytics(report_data, conn, session["parent_grade"])
        else:
            logging.info(
                "No report found for student, checking available tables for fallback"
            )
            # Fallback: fetch data directly from marksheet table
            grade = session["parent_grade"]
            table_mapping = {
                "playgroup": "playgroup_marks",
                "pp1": "pp1_marks",
                "pp2": "pp2_marks",
                "Grade 1": "lower_marks",
                "Grade 2": "lower_marks",
                "Grade 3": "lower_marks",
                "Grade 4": "primary_marks",
                "Grade 7": "marks",
                "Grade 8": "marks",
                "Grade 9": "marks",
            }
            table = table_mapping.get(grade)
            if table:
                # Check if table exists before querying
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                table_exists = cursor.fetchone()
                # Log available tables for debugging
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                all_tables = [row[0] for row in cursor.fetchall()]
                logging.info(f"Fallback: Available tables in database: {all_tables}")
                logging.info(
                    f"Fallback: Looking for table '{table}' for grade '{grade}'"
                )
                if table_exists:
                    conn.execute(
                        f"SELECT * FROM {table} WHERE adm_no = ?",
                        (session["parent_adm_no"],),
                    )
                    columns = [desc[0] for desc in conn.description]
                    row = conn.fetchone()
                    if row:
                        current_marks = dict(zip(columns, row))
                        # Use average_points for junior, average_level for others
                        if grade in ["Grade 7", "Grade 8", "Grade 9"]:
                            if "average_points" in current_marks:
                                if current_marks["average_points"]:
                                    # Check if average_points is already a rating string or needs conversion
                                    avg_points = current_marks["average_points"]
                                    if isinstance(avg_points, str) and avg_points in [
                                        "EE1",
                                        "EE2",
                                        "ME1",
                                        "ME2",
                                        "AE1",
                                        "AE2",
                                        "BE1",
                                        "BE2",
                                    ]:
                                        # Already a rating string, use it directly
                                        current_marks["average_level"] = avg_points
                                    else:
                                        # Convert numeric average_points to rating string
                                        try:
                                            avg_points_float = float(avg_points)
                                            current_marks["average_level"] = (
                                                points_to_rating(avg_points_float)
                                            )
                                        except (ValueError, TypeError):
                                            # If conversion fails, use as-is or default
                                            current_marks["average_level"] = (
                                                avg_points
                                                if isinstance(avg_points, str)
                                                else ""
                                            )
                                else:
                                    current_marks["average_level"] = ""
                        report_data = {
                            "current_marks": current_marks,
                            "exam_title": (
                                current_exam_title
                                if "current_exam_title" in locals()
                                else "Current Exam"
                            ),
                            "previous_exams": [],
                        }
                    # Log subject-related keys for debugging
                    subject_keys = [
                        k
                        for k in current_marks.keys()
                        if "scie" in k.lower() or "int" in k.lower()
                    ]
                    logging.info(
                        f"Fallback: Retrieved data from {table} with subject keys: {subject_keys}"
                    )
                    logging.info(
                        f"Fallback: All keys: {list(current_marks.keys())[:15]}"
                    )
                    # Log actual values for int_scie columns
                    if "int_scie_s" in current_marks:
                        logging.info(
                            f"Fallback: int_scie_s = {current_marks['int_scie_s']}"
                        )
                    if "int_scie_r" in current_marks:
                        logging.info(
                            f"Fallback: int_scie_r = {current_marks['int_scie_r']}"
                        )
                    if "int_scie_p" in current_marks:
                        logging.info(
                            f"Fallback: int_scie_p = {current_marks['int_scie_p']}"
                        )
                    if "average_points" in current_marks:
                        logging.info(
                            f"Fallback: average_points = {current_marks['average_points']}"
                        )
                    if "average_level" in current_marks:
                        logging.info(
                            f"Fallback: average_level = {current_marks['average_level']}"
                        )
                else:
                    logging.warning(
                        f"Fallback: Table '{table}' does not exist in cloud database"
                    )
                    report_data = None
            else:
                logging.warning(f"Fallback: No table mapping found for grade '{grade}'")
                report_data = None

        # Always use current_exam_title from school_config.json to override report data
        # Load school_config.json to get current_exam_title
        import json
        import os

        config_path = os.path.join(os.path.dirname(__file__), "school_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                current_exam_title = config.get("current_exam_title", "Current Exam")
                logging.info(
                    f"Using current_exam_title from school_config.json: {current_exam_title}"
                )
        else:
            # Fallback to grade-specific titles if config not found
            grade = session["parent_grade"]
            grade_lower = grade.lower() if grade else ""
            current_exam_title = "Current Exam"

            if grade_lower in ["playgroup", "pp1", "pp2"]:
                current_exam_title = "TERM ASSESSMENT"
            elif grade_lower in [
                "grade 1",
                "grade 2",
                "grade 3",
                "grade 4",
                "grade 5",
                "grade 6",
            ]:
                current_exam_title = "PRIMARY EXAM"
            elif grade_lower in ["grade 7", "grade 8", "grade 9"]:
                current_exam_title = "JSS ASSESSMENT"

            logging.info(
                f"Using fallback exam_title for grade {grade}: {current_exam_title}"
            )

        # Only override report_data exam_title if it's missing or empty
        # Otherwise use the exam_title from the report data sent by desktop app
        if report_data:
            if not report_data.get("exam_title") or report_data.get("exam_title") == "":
                report_data["exam_title"] = current_exam_title
                logging.info(
                    f"Report_data exam_title was missing, using school_config value: {current_exam_title}"
                )
            else:
                logging.info(
                    f"Using report_data exam_title from desktop app: {report_data.get('exam_title')}"
                )

        # Use previous exams from report data if available
        if report_data and "previous_exams" in report_data:
            previous_exams_list = report_data["previous_exams"]
            logging.info(
                f"Using {len(previous_exams_list)} previous exams from report data"
            )

            # Database already returns exams in DESC order (newest first), so no reversal needed
            # previous_exams_list = list(reversed(previous_exams_list))

            # Convert to format expected by template
            previous_exams = []
            previous_exam_marks = {}
            for prev_exam in previous_exams_list:
                previous_exams.append(
                    {
                        "exam_title": prev_exam["exam_name"],
                        "exam_date": prev_exam["exam_date"],
                        "average_level": prev_exam.get("average_level"),
                        "total_points": prev_exam.get("total_points"),
                    }
                )
                marks = prev_exam["marks"]
                # Parse marks if it's a JSON string
                if isinstance(marks, str):
                    try:
                        marks = json.loads(marks)
                        logging.info(
                            f"Parsed marks from JSON string for exam {prev_exam['exam_name']}"
                        )
                    except:
                        logging.error(
                            f"Failed to parse marks as JSON for exam {prev_exam['exam_name']}"
                        )
                        marks = {}
                previous_exam_marks[prev_exam["exam_name"]] = marks
                # Older desktop versions may not include an exam average. Derive
                # it from the subject ratings so the template/chart doesn't fall
                # back to BE2 when ratings are available.
                exam_entry = previous_exams[-1]
                if not exam_entry.get("average_level") and isinstance(marks, dict):
                    rating_points = []
                    for mark in marks.values():
                        rating = mark.get("rating") if isinstance(mark, dict) else mark
                        points = rating_to_points(str(rating).strip()) if rating else 0
                        if points:
                            rating_points.append(points)
                    if rating_points:
                        exam_entry["average_level"] = points_to_rating(
                            sum(rating_points) / len(rating_points)
                        )
                        logging.info(
                            "Derived previous exam average_level=%s for %s from %d subject ratings",
                            exam_entry["average_level"],
                            prev_exam["exam_name"],
                            len(rating_points),
                        )
                logging.info(
                    f"Previous exam: {prev_exam['exam_name']}, marks type: {type(marks)}, is dict: {isinstance(marks, dict)}, is list: {isinstance(marks, list)}"
                )
                if isinstance(marks, dict):
                    logging.info(f"  marks keys: {list(marks.keys())[:5]}")
                    logging.info(f"  marks sample: {list(marks.items())[:2]}")
                    # Log complete structure for MOCK exam to debug score/rating/points issue
                    if prev_exam["exam_name"] == "MOCK":
                        logging.info(f"  MOCK exam complete marks structure: {marks}")
                elif isinstance(marks, list):
                    logging.info(f"  marks length: {len(marks)}")
                    logging.info(f"  marks sample: {marks[:5]}")
            logging.info(
                f"previous_exam_marks keys: {list(previous_exam_marks.keys())}"
            )
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
            (session["parent_school_name"],),
        ).fetchone()

        school_address = school["school_address"] if school else None
        school_telephone = school["school_telephone"] if school else None
        school_logo = school["school_logo"] if school else None
        school_administrator = (
            school["school_administrator"] if school else "School Administrator"
        )
        school_signature = school["school_signature"] if school else ""

        logging.info(
            f"School details - administrator: {school_administrator}, signature: {'present' if school_signature else 'missing'}"
        )

        # Log current marks keys for debugging
        if report_data:
            current_marks_keys = list(report_data.get("current_marks", {}).keys())
            logging.info(f"Current marks keys (first 10): {current_marks_keys[:10]}")
        else:
            current_marks_keys = []
            logging.info("No report data available, current_marks_keys set to empty")
        # Extract subject names from current marks keys
        subject_names = []
        for key in current_marks_keys:
            if key.endswith("_s") and key not in [
                "total_points_s",
                "average_level_s",
                "rank_s",
            ]:
                # Use rstrip to only remove the '_s' suffix, not all occurrences
                subject_name = key.rstrip("_s").replace("_", " ").title()
                subject_names.append(subject_name)
        logging.info(f"Subject names from current marks: {subject_names}")

        # Log the complete previous_exam_marks structure for debugging
        logging.info(f"Complete previous_exam_marks structure: {previous_exam_marks}")
        for exam_title, marks in previous_exam_marks.items():
            logging.info(
                f"  {exam_title}: type={type(marks)}, is_dict={isinstance(marks, dict)}, keys={list(marks.keys()) if isinstance(marks, dict) else 'N/A'}"
            )
        logging.info(f"previous_exams list for template: {previous_exams}")
        for prev_exam in previous_exams:
            logging.info(
                f"  exam_title: '{prev_exam.get('exam_title')}', will lookup in previous_exam_marks"
            )

        # Fetch student photo and stream from database
        student = conn.execute(
            """
            SELECT photo, stream FROM students
            WHERE student_name = ? AND adm_no = ?
            """,
            (session["parent_student_name"], session["parent_adm_no"]),
        ).fetchone()

        # The desktop report now carries a compressed data URL. Prefer it over
        # a local path from the cloud students table (which may not exist here).
        student_photo = (
            report_data.get("photo")
            if isinstance(report_data, dict) and report_data.get("photo")
            else (student["photo"] if student and student["photo"] else None)
        )
        if student_photo and not str(student_photo).startswith(("http://", "https://", "data:image/")):
            # Handle photos stored as paths on the cloud host, if any.
            student_photo = image_to_base64(student_photo) or None
        student_stream = student["stream"] if student and student["stream"] else "None"

        # Fetch school_id from database using school_name
        school = conn.execute(
            "SELECT id FROM schools WHERE school_name = ?",
            (session["parent_school_name"],),
        ).fetchone()

        school_id = school["id"] if school else None

        # Fetch teacher assignments for this grade
        teacher_assignments = conn.execute(
            """
            SELECT subject, teacher_name FROM teacher_assignments
            WHERE school_id = ? AND class_name = ?
            """,
            (school_id, session["parent_grade"]),
        ).fetchall()

        # Create a dictionary mapping subject to teacher name
        teacher_map = {
            row["subject"]: row["teacher_name"] for row in teacher_assignments
        }

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
            teacher_map=teacher_map,
        )
    except Exception as e:
        logging.error(f"Parent dashboard error: {e}", exc_info=True)
        session.pop('_flashes', None)
        flash("An error occurred loading the dashboard.", "error")
        return redirect(url_for("parent_login"))
    finally:
        conn.close()


@app.route("/parent/newsletters")
def parent_newsletters():
    if "parent_student_id" not in session:
        return redirect(url_for("parent_login"))

    # Check payment status before allowing newsletter access
    if session.get("payment_status") == "unpaid":
        session.pop('_flashes', None)
        flash(
            "⚠️ PAYMENT REQUIRED: You cannot view newsletters until the required payment is made. "
            "Please contact the school administration for payment details.",
            "error"
        )
        return redirect(url_for("parent_dashboard"))

    # Get newsletters for this parent's student class
    conn = get_db()
    try:
        student_grade = session.get("parent_grade")
        student_id = session.get("parent_student_id")

        logging.info(
            f"Fetching newsletters for student_id={student_id}, grade={student_grade}"
        )

        # Check if portal_announcements table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='portal_announcements'"
        )
        table_exists = cursor.fetchone()

        if not table_exists:
            # Table doesn't exist, return empty list
            logging.warning("portal_announcements table does not exist")
            newsletters = []
        else:
            # Get all newsletters for debugging
            all_newsletters = conn.execute(
                "SELECT * FROM portal_announcements"
            ).fetchall()
            logging.info(f"All newsletters in database: {len(all_newsletters)}")
            for nl in all_newsletters:
                logging.info(
                    f"  - ID: {nl[0]}, class_context: {nl[5]}, subject: {nl[2]}"
                )

            # Get newsletters from portal_announcements table with view status
            newsletters = conn.execute(
                """
                SELECT pa.*, n.attachment_path,
                       COALESCE(pvs.has_viewed, 0) as has_viewed
                FROM portal_announcements pa
                LEFT JOIN newsletters n ON pa.newsletter_id = n.id
                LEFT JOIN parent_view_status pvs ON pvs.content_id = pa.id 
                    AND pvs.content_type = 'newsletter' 
                    AND pvs.student_id = ?
                WHERE pa.class_context = ? OR pa.class_context = 'All Classes'
                ORDER BY pa.published_at DESC
            """,
                (student_id, student_grade),
            ).fetchall()

            logging.info(
                f"Filtered newsletters for grade {student_grade}: {len(newsletters)}"
            )

        return render_template(
            "cloud_parent_newsletters.html",
            newsletters=newsletters,
            school_name=session.get("parent_school_name"),
            student_name=session.get("parent_student_name"),
        )
    except Exception as e:
        logging.error(f"Error fetching newsletters: {e}", exc_info=True)
        # Return empty list on error
        return render_template(
            "cloud_parent_newsletters.html",
            newsletters=[],
            school_name=session.get("parent_school_name"),
            student_name=session.get("parent_student_name"),
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
        conn.execute(
            """
            INSERT OR REPLACE INTO parent_view_status 
            (student_id, content_type, content_id, has_viewed, viewed_at)
            VALUES (?, 'newsletter', ?, 1, CURRENT_TIMESTAMP)
        """,
            (student_id, newsletter_id),
        )

        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


def generate_analytics(report_data, conn, grade):
    """Generate analytics data for parent dashboard including trends, comparisons, and comments"""
    if not report_data or "current_marks" not in report_data:
        return report_data

    current_marks = report_data["current_marks"]

    # Convert average_points to average_level for junior grades
    if grade in ["Grade 7", "Grade 8", "Grade 9"]:
        if "average_points" in current_marks:
            if current_marks["average_points"]:
                # Check if average_points is already a rating string or needs conversion
                avg_points = current_marks["average_points"]
                if isinstance(avg_points, str) and avg_points in [
                    "EE1",
                    "EE2",
                    "ME1",
                    "ME2",
                    "AE1",
                    "AE2",
                    "BE1",
                    "BE2",
                ]:
                    # Already a rating string, use it directly
                    current_marks["average_level"] = avg_points
                else:
                    # Convert numeric average_points to rating string
                    try:
                        avg_points_float = float(avg_points)
                        current_marks["average_level"] = points_to_rating(
                            avg_points_float
                        )
                    except (ValueError, TypeError):
                        # If conversion fails, use as-is or default
                        current_marks["average_level"] = (
                            avg_points if isinstance(avg_points, str) else ""
                        )
            else:
                current_marks["average_level"] = ""

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

        subject_analysis.append(
            {
                "name": subject,
                "current_score": current_score,
                "previous_1": current_score - 5,  # Mock previous score
                "previous_2": current_score - 10,  # Mock previous score
                "trend": trend,
                "improvement": improvement,
                "decline": decline,
                "class_average": class_average,
                "performance": performance,
            }
        )

        subject_names.append(subject)
        student_scores.append(current_score)
        class_averages.append(class_average)

    # Generate overall trend
    total_points = current_marks.get("total_points", 0)
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
    report_data["subject_analysis"] = subject_analysis
    report_data["trend"] = overall_trend
    report_data["overall_comment"] = overall_comment
    report_data["subject_comments"] = subject_comments
    report_data["recommendations"] = recommendations
    report_data["exam_labels"] = exam_labels
    report_data["exam_scores"] = exam_scores
    report_data["subject_names"] = subject_names
    report_data["student_scores"] = student_scores
    report_data["class_averages"] = class_averages

    return report_data


def get_subjects_for_grade(grade):
    """Get subjects for a specific grade"""
    # First try to get from database if school_id is in session
    if "school_id" in session:
        conn = get_db()
        try:
            school = conn.execute(
                "SELECT subjects FROM schools WHERE id = ?", (session["school_id"],)
            ).fetchone()
            if school and school["subjects"]:
                try:
                    subjects_data = json.loads(school["subjects"])
                    # Map grade name to config key (e.g., "Grade 1" -> "lower")
                    config_key = map_grade_to_config_key(grade)
                    subjects = subjects_data.get(config_key, [])
                    # If not found with mapped key, try original grade name
                    if not subjects:
                        subjects = subjects_data.get(grade, [])
                    if subjects:
                        return subjects
                except (json.JSONDecodeError, TypeError):
                    pass
        finally:
            conn.close()
    
    # Fall back to hardcoded mapping
    return GRADE_SUBJECTS.get(grade, [])


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
        score = subject["current_score"]
        performance = subject["performance"]

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

        comments.append(
            {"subject": subject["name"], "comment": comment, "type": comment_type}
        )

    return comments


def generate_recommendations(subject_analysis, total_points):
    """Generate recommendations for improvement"""
    recommendations = []

    # Analyze weak subjects
    weak_subjects = [s for s in subject_analysis if s["current_score"] < 40]
    if weak_subjects:
        recommendations.append(
            f"Focus additional practice time on: {', '.join([s['name'] for s in weak_subjects])}"
        )

    # Analyze strong subjects
    strong_subjects = [s for s in subject_analysis if s["current_score"] >= 70]
    if strong_subjects:
        recommendations.append(
            f"Continue to excel in: {', '.join([s['name'] for s in strong_subjects])}"
        )

    # General recommendations
    if total_points < 30:
        recommendations.append(
            "Consider seeking extra help from teachers or tutors in challenging subjects."
        )
        recommendations.append(
            "Establish a consistent study routine with dedicated time for each subject."
        )
    elif total_points < 40:
        recommendations.append("Set specific goals for improvement in each subject.")
        recommendations.append(
            "Review class notes regularly and complete all assignments on time."
        )
    else:
        recommendations.append(
            "Maintain current study habits and continue to challenge yourself."
        )
        recommendations.append(
            "Consider helping peers who may be struggling in subjects you excel in."
        )

    return recommendations


@app.route("/parent/logout")
def parent_logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    # Initialize FCM service at startup
    try:
        from fcm_service import get_fcm_service

        fcm_service = get_fcm_service()
        logging.info(
            f"FCM Service initialized at startup: Available={fcm_service.is_available()}"
        )
    except Exception as e:
        logging.error(f"Failed to initialize FCM service at startup: {e}")

    # Crucial for Railway: Listen on 0.0.0.0 and use the dynamic PORT variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
