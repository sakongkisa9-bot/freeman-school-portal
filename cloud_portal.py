from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import json
from datetime import datetime

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, 'cloud_portal.db')

GRADE_OPTIONS = [
    'Playgroup', 'Pre-Primary 1', 'Pre-Primary 2',
    'Grade 1', 'Grade 2', 'Grade 3',
    'Grade 4', 'Grade 5', 'Grade 6',
    'Grade 7', 'Grade 8', 'Grade 9'
]

GRADE_SUBJECTS = {
    'Playgroup': ['LANG', 'MATH', 'CREAT', 'ENV'],
    'Pre-Primary 1': ['LANG', 'MATH', 'ENV', 'PSYCH', 'REL'],
    'Pre-Primary 2': ['LANG', 'MATH', 'ENV', 'PSYCH', 'REL'],
    'Grade 1': ['ENG', 'KISW', 'MAT', 'ENV', 'LIT', 'CRE', 'ART', 'MOV'],
    'Grade 2': ['ENG', 'KISW', 'MAT', 'ENV', 'LIT', 'CRE', 'ART', 'MOV'],
    'Grade 3': ['ENG', 'KISW', 'MAT', 'ENV', 'LIT', 'CRE', 'ART', 'MOV'],
    'Grade 4': ['ENG', 'KISW', 'MATH', 'SCIE', 'AGRI', 'SST', 'CRE', 'C/A', 'PHE'],
    'Grade 5': ['ENG', 'KISW', 'MATH', 'SCIE', 'AGRI', 'SST', 'CRE', 'C/A', 'PHE'],
    'Grade 6': ['ENG', 'KISW', 'MATH', 'SCIE', 'AGRI', 'SST', 'CRE', 'C/A', 'PHE'],
    'Grade 7': ['MATH', 'ENG', 'KISW', 'INT SCIE', 'PRE-TECH', 'SST', 'CRE', 'AGRI', 'C/A'],
    'Grade 8': ['MATH', 'ENG', 'KISW', 'INT SCIE', 'PRE-TECH', 'SST', 'CRE', 'AGRI', 'C/A'],
    'Grade 9': ['MATH', 'ENG', 'KISW', 'INT SCIE', 'PRE-TECH', 'SST', 'CRE', 'AGRI', 'C/A']
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT NOT NULL,
            school_code TEXT NOT NULL UNIQUE,
            email TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute('''
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
    ''')
    cursor.execute('''
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
    ''')
    cursor.execute('''
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
    ''')
    conn.commit()
    try:
        cursor.execute('ALTER TABLE teachers ADD COLUMN email TEXT')
    except Exception:
        pass
    try:
        cursor.execute('ALTER TABLE students ADD COLUMN gender TEXT')
    except Exception:
        pass
    try:
        cursor.execute('ALTER TABLE students ADD COLUMN phone TEXT')
    except Exception:
        pass
    conn.commit()
    conn.close()


def get_school_by_code(school_code):
    conn = get_db()
    row = conn.execute('SELECT * FROM schools WHERE school_code = ?', (school_code,)).fetchone()
    conn.close()
    return row


def get_teacher(school_id, username):
    conn = get_db()
    row = conn.execute('SELECT * FROM teachers WHERE school_id = ? AND username = ?', (school_id, username)).fetchone()
    conn.close()
    return row


def authenticate_user(school_code, username, password):
    school = get_school_by_code(school_code)
    if not school:
        return None, 'School code not found.'
    teacher = get_teacher(school['id'], username)
    if not teacher or not check_password_hash(teacher['password_hash'], password):
        return None, 'Invalid username or password.'
    return {'school': school, 'teacher': teacher}, None


def get_students_for_grade(school_id, grade):
    conn = get_db()
    rows = conn.execute('SELECT * FROM students WHERE school_id = ? AND grade = ? ORDER BY adm_no', (school_id, grade)).fetchall()
    conn.close()
    return rows


def get_marks_for_grade(school_id, grade, exam_title):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM marks WHERE school_id = ? AND grade = ? AND exam_title = ? ORDER BY adm_no',
        (school_id, grade, exam_title)
    ).fetchall()
    conn.close()
    return rows


def save_marks_records(school_id, grade, exam_title, records):
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    for item in records:
        student_name = item.get('name', '')
        adm_no = item.get('adm_no', '')
        subject_scores_json = json.dumps(item.get('scores', {}))
        total_points = item.get('total_points', '')
        average_level = item.get('average_level', '')
        cursor.execute('''
            INSERT INTO marks (school_id, grade, adm_no, student_name, exam_title, subject_scores_json, total_points, average_level, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(school_id, grade, adm_no, exam_title) DO UPDATE SET
                student_name = excluded.student_name,
                subject_scores_json = excluded.subject_scores_json,
                total_points = excluded.total_points,
                average_level = excluded.average_level,
                updated_at = excluded.updated_at
        ''', (school_id, grade, adm_no, student_name, exam_title, subject_scores_json, total_points, average_level, now))
    conn.commit()
    conn.close()


def save_students_records(school_id, students):
    conn = get_db()
    cursor = conn.cursor()
    for item in students:
        student_name = item.get('name', '')
        adm_no = item.get('adm_no', '')
        grade = item.get('grade', '')
        gender = item.get('gender', '')
        phone = item.get('phone', '')
        if not (student_name and adm_no and grade):
            continue
        cursor.execute('''
            INSERT INTO students (school_id, grade, adm_no, student_name, gender, phone)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(school_id, grade, adm_no) DO UPDATE SET
                student_name = excluded.student_name,
                gender = excluded.gender,
                phone = excluded.phone
        ''', (school_id, grade, adm_no, student_name, gender, phone))
    conn.commit()
    conn.close()


@app.before_request
def ensure_database():
    init_db()


@app.route('/')
def home():
    return render_template('cloud_home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        school_name = request.form.get('school_name', '').strip()
        school_code = request.form.get('school_code', '').strip().lower()
        school_email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip().lower()
        teacher_email = request.form.get('teacher_email', '').strip().lower()
        password = request.form.get('password', '')

        if not school_name or not school_code or not username or not password:
            flash('School name, school code, username and password are required.', 'danger')
            return redirect(url_for('register'))

        conn = get_db()
        try:
            password_hash = generate_password_hash(password)
            now = datetime.utcnow().isoformat()
            conn.execute('INSERT INTO schools (school_name, school_code, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)',
                         (school_name, school_code, school_email, password_hash, now))
            school_id = conn.execute('SELECT id FROM schools WHERE school_code = ?', (school_code,)).fetchone()['id']
            conn.execute('INSERT INTO teachers (school_id, username, password_hash, email, role, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                         (school_id, username, password_hash, teacher_email, 'admin', now))
            conn.commit()
            flash('School registration completed. Use your teacher login to sign in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('The school code or username is already in use. Choose a different code.', 'danger')
            return redirect(url_for('register'))
        finally:
            conn.close()

    return render_template('cloud_register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        school_code = request.form.get('school_code', '').strip().lower()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        auth, error = authenticate_user(school_code, username, password)
        if error:
            flash(error, 'danger')
            return redirect(url_for('login'))

        session['school_id'] = auth['school']['id']
        session['school_name'] = auth['school']['school_name']
        session['username'] = auth['teacher']['username']
        session['grade'] = 'Grade 1'
        return redirect(url_for('dashboard'))

    return render_template('cloud_login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/dashboard')
def dashboard():
    if 'school_id' not in session:
        return redirect(url_for('login'))
    return render_template('cloud_dashboard.html', school_name=session.get('school_name'), username=session.get('username'), grades=GRADE_OPTIONS)


@app.route('/students/<grade>', methods=['GET', 'POST'])
def manage_students(grade):
    if 'school_id' not in session:
        return redirect(url_for('login'))

    students = get_students_for_grade(session['school_id'], grade)

    if request.method == 'POST':
        student_name = request.form.get('student_name', '').strip()
        adm_no = request.form.get('adm_no', '').strip()
        gender = request.form.get('gender', '').strip()
        phone = request.form.get('phone', '').strip()
        if not student_name or not adm_no:
            flash('Student name and admission number are required.', 'danger')
            return redirect(url_for('manage_students', grade=grade))

        conn = get_db()
        try:
            conn.execute('''
                INSERT INTO students (school_id, grade, adm_no, student_name, gender, phone)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(school_id, grade, adm_no) DO UPDATE SET
                    student_name = excluded.student_name,
                    gender = excluded.gender,
                    phone = excluded.phone
            ''', (session['school_id'], grade, adm_no, student_name, gender, phone))
            conn.commit()
            flash('Student added successfully.', 'success')
        except Exception as e:
            flash(f'Could not add student: {e}', 'danger')
        finally:
            conn.close()

        return redirect(url_for('manage_students', grade=grade))

    return render_template('cloud_students.html', grade=grade, students=students)


@app.route('/marks/<grade>', methods=['GET', 'POST'])
def enter_marks(grade):
    if 'school_id' not in session:
        return redirect(url_for('login'))

    subjects = GRADE_SUBJECTS.get(grade, [])
    students = get_students_for_grade(session['school_id'], grade)
    exam_title = request.args.get('exam_title', 'TERM 1 EXAM 2026')
    marks = get_marks_for_grade(session['school_id'], grade, exam_title)
    marks_map = {row['adm_no']: json.loads(row['subject_scores_json']) for row in marks}

    if request.method == 'POST':
        exam_title = request.form.get('exam_title', '').strip() or 'TERM 1 EXAM 2026'
        records = []
        for student in students:
            adm_no = student['adm_no']
            row_scores = {}
            for subject in subjects:
                score = request.form.get(f'score_{adm_no}_{subject}', '').strip()
                rating = request.form.get(f'rating_{adm_no}_{subject}', '').strip()
                points = request.form.get(f'points_{adm_no}_{subject}', '').strip()
                if score or rating or points:
                    row_scores[subject] = {'score': score, 'rating': rating, 'points': points}

            total_points = request.form.get(f'total_{adm_no}', '').strip()
            average_level = request.form.get(f'average_{adm_no}', '').strip()
            records.append({
                'adm_no': adm_no,
                'name': student['student_name'],
                'scores': row_scores,
                'total_points': total_points,
                'average_level': average_level
            })

        save_marks_records(session['school_id'], grade, exam_title, records)
        flash('Marks saved successfully.', 'success')
        return redirect(url_for('enter_marks', grade=grade, exam_title=exam_title))

    return render_template('cloud_marks.html', grade=grade, subjects=subjects, students=students, marks_map=marks_map, exam_title=exam_title)


@app.route('/api/fetch_marks', methods=['POST'])
def api_fetch_marks():
    data = request.get_json(force=True)
    if not data:
        return jsonify({'success': False, 'message': 'JSON body is required.'}), 400

    school_code = data.get('school_code', '').strip().lower()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    grade = data.get('grade', '')

    auth, error = authenticate_user(school_code, username, password)
    if error:
        return jsonify({'success': False, 'message': error}), 401

    students = get_students_for_grade(auth['school']['id'], grade)
    exam_title = data.get('exam_title', 'TERM 1 EXAM 2026')
    marks = get_marks_for_grade(auth['school']['id'], grade, exam_title)
    marks_map = {row['adm_no']: json.loads(row['subject_scores_json']) for row in marks}

    records = []
    for student in students:
        record = {
            'adm_no': student['adm_no'],
            'name': student['student_name'],
            'scores': marks_map.get(student['adm_no'], {}),
            'total_points': '',
            'average_level': ''
        }
        matching_mark = next((m for m in marks if m['adm_no'] == student['adm_no']), None)
        if matching_mark:
            record['total_points'] = matching_mark['total_points']
            record['average_level'] = matching_mark['average_level']
        records.append(record)

    return jsonify({'success': True, 'grade': grade, 'exam_title': exam_title, 'records': records, 'subjects': GRADE_SUBJECTS.get(grade, [])})


@app.route('/api/save_marks', methods=['POST'])
def api_save_marks():
    data = request.get_json(force=True)
    if not data:
        return jsonify({'success': False, 'message': 'JSON body is required.'}), 400

    school_code = data.get('school_code', '').strip().lower()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    grade = data.get('grade', '')
    exam_title = data.get('exam_title', 'TERM 1 EXAM 2026')
    records = data.get('records', [])

    auth, error = authenticate_user(school_code, username, password)
    if error:
        return jsonify({'success': False, 'message': error}), 401

    if not grade or not records:
        return jsonify({'success': False, 'message': 'Grade and records are required.'}), 400

    save_marks_records(auth['school']['id'], grade, exam_title, records)
    return jsonify({'success': True, 'message': 'Marks saved to cloud portal.'})


@app.route('/api/upload_students', methods=['POST'])
def api_upload_students():
    data = request.get_json(force=True)
    if not data:
        return jsonify({'success': False, 'message': 'JSON body is required.'}), 400

    school_code = data.get('school_code', '').strip().lower()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    students = data.get('students', [])

    auth, error = authenticate_user(school_code, username, password)
    if error:
        return jsonify({'success': False, 'message': error}), 401

    if not students:
        return jsonify({'success': False, 'message': 'Student list is required.'}), 400

    save_students_records(auth['school']['id'], students)
    return jsonify({'success': True, 'message': 'Student roster synced to cloud portal.'})


@app.route('/api/fetch_students', methods=['POST'])
def api_fetch_students():
    data = request.get_json(force=True)
    if not data:
        return jsonify({'success': False, 'message': 'JSON body is required.'}), 400

    school_code = data.get('school_code', '').strip().lower()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    grade = data.get('grade', '')

    auth, error = authenticate_user(school_code, username, password)
    if error:
        return jsonify({'success': False, 'message': error}), 401

    students = get_students_for_grade(auth['school']['id'], grade)
    records = []
    for student in students:
        records.append({
            'adm_no': student['adm_no'],
            'name': student['student_name'],
            'gender': student.get('gender', ''),
            'phone': student.get('phone', ''),
            'grade': student['grade']
        })
    return jsonify({'success': True, 'grade': grade, 'records': records})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
