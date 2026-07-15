from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import json

app = Flask(__name__)

# --- PATH CONFIGURATION ---
# We use the same absolute path logic as the desktop app to ensure they share the file
PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, "freeman_data.db")
JSON_PATH = os.path.join(PROJECT_DIR, "school_config.json")
GRADE_OPTIONS = [
    "Play group", "Pre-Primary 1", "Pre-Primary 2",
    "Grade 1", "Grade 2", "Grade 3",
    "Grade 4", "Grade 5", "Grade 6",
    "Grade 7", "Grade 8", "Grade 9"
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    return conn

# NEW: Pulls everything directly from the JSON Wizard file
def get_config_data():
    try:
        if os.path.exists(JSON_PATH):
            with open(JSON_PATH, 'r') as f:
                config = json.load(f)
                return config
    except Exception as e:
        print(f"JSON Load Error in Flask: {e}")
    
    # Fallback if JSON is missing or broken
    return {
        "school_name": "FREEMAN TECH",
        "portal_title": "OFFICIAL MARKING PORTAL",
        "subjects": {
            "playgroup": [],
            "pp1": [],
            "pp2": [],
            "lower": [],
            "primary": [],
            "jss": []
        }
    }


def get_grade_type(grade_name):
    if not grade_name:
        return "primary"
    name = grade_name.strip().lower()
    if "play group" in name or "playgroup" in name:
        return "playgroup"
    if "pre-primary 1" in name or "pp1" in name:
        return "pp1"
    if "pre-primary 2" in name or "pp2" in name:
        return "pp2"
    if any(x in name for x in ["grade 1", "grade 2", "grade 3"]):
        return "lower"
    if any(x in name for x in ["grade 4", "grade 5", "grade 6"]):
        return "primary"
    if any(x in name for x in ["grade 7", "grade 8", "grade 9"]):
        return "jss"
    return "primary"

@app.route('/')
def index():
    config = get_config_data()
    school = config.get("school_name", "FREEMAN TECH")
    
    # We pass the subject lists to index.html for the dropdowns
    subjects = config.get("subjects", {})
    playgroup_subs = subjects.get("playgroup", [])
    pp1_subs = subjects.get("pp1", [])
    pp2_subs = subjects.get("pp2", [])
    lower_subs = subjects.get("lower", [])
    primary_subs = subjects.get("primary", [])
    jss_subs = subjects.get("jss", [])
    
    return render_template('index.html', 
                           mode="home", 
                           school_name=school, 
                           portal_title="STAFF MARKING PORTAL",
                           grade_options=GRADE_OPTIONS,
                           playgroup_subjects=playgroup_subs,
                           pp1_subjects=pp1_subs,
                           pp2_subjects=pp2_subs,
                           lower_subjects=lower_subs,
                           primary_subjects=primary_subs,
                           jss_subjects=jss_subs)

@app.route('/enter_marks')
def enter_marks():
    config = get_config_data()
    school = config.get("school_name", "FREEMAN TECH")
    
    grade = request.args.get('grade')
    subject = request.args.get('subject') # This is now the clean code from the dropdown
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT adm_no, name FROM students WHERE grade = ?", (grade,))
    students = [{"adm_no": row[0], "name": row[1]} for row in cursor.fetchall()]
    conn.close()

    return render_template('index.html', mode="marking", 
                           students=students, grade=grade, 
                           subject=subject, school_name=school, 
                           portal_title="MARKS ENTRY MODE")

# ... (keep your rating and submit functions exactly as they are) ...

def get_grade_7_8_rating(score):
    if not score or str(score).strip() == "":
        return "BE2", 0
    try:
        s = int(score)
        if s >= 90: return "EE1", 8
        elif s >= 75: return "EE2", 7
        elif s >= 58: return "ME1", 6
        elif s >= 41: return "ME2", 5
        elif s >= 31: return "AE1", 4
        elif s >= 21: return "AE2", 3
        elif s >= 11: return "BE1", 2
        else: return "BE2", 1
    except: return "BE2", 0

def get_grade_4_6_rating(score):
    if not score or str(score).strip() == "":
        return "BE2"
    try:
        s = int(score)
        if s >= 90: return "EE1"
        elif s >= 75: return "EE2"
        elif s >= 58: return "ME1"
        elif s >= 41: return "ME2"
        elif s >= 31: return "AE1"
        elif s >= 21: return "AE2"
        elif s >= 11: return "BE1"
        else: return "BE2"
    except: return "BE2"

def calculate_final_level(total_val, is_primary=False):
    if is_primary:
        if total_val >= 540: return "EE1"
        elif total_val >= 450: return "EE2"
        elif total_val >= 348: return "ME1"
        elif total_val >= 246: return "ME2"
        elif total_val >= 186: return "AE1"
        elif total_val >= 126: return "AE2"
        elif total_val >= 66: return "BE1"
        return "BE2"
    else:
        if total_val >= 66: return "EE1"
        elif total_val >= 58: return "EE2"
        elif total_val >= 48: return "ME1"
        elif total_val >= 38: return "ME2"
        elif total_val >= 28: return "AE1"
        elif total_val >= 18: return "AE2"
        elif total_val >= 9: return "BE1"
        return "BE2"

@app.route('/submit', methods=['POST'])
def submit():
    subject = request.form.get('subject').lower().replace(" ", "_")
    grade_name = request.form.get('grade')
    grade_type = get_grade_type(grade_name)
    
    is_junior = grade_type == "jss"
    table_name_map = {
        "playgroup": "playgroup_marks",
        "pp1": "pp1_marks",
        "pp2": "pp2_marks",
        "lower": "lower_marks",
        "primary": "primary_marks",
        "jss": "marksheet"
    }
    table_name = table_name_map.get(grade_type, "primary_marks")
    
    conn = get_db()
    cursor = conn.cursor()
    
    def safe_int(value):
        try:
            if value is None or str(value).strip() == "":
                return 0
            return int(value)
        except:
            return 0

    try:
        for adm, score in request.form.items():
            if adm not in ['subject', 'grade']:
                adm = adm.strip()
                score_val = score if score and score.strip() != "" else "0"
                
                if is_junior:
                    rate, points = get_grade_7_8_rating(score_val)
                    cursor.execute(f"SELECT 1 FROM marksheet WHERE adm_no = ?", (adm,))
                    if cursor.fetchone():
                        cursor.execute(f"UPDATE marksheet SET {subject}_s=?, {subject}_r=?, {subject}_p=? WHERE adm_no=?", (score_val, rate, points, adm))
                    else:
                        cursor.execute(f"INSERT INTO marksheet (adm_no, {subject}_s, {subject}_r, {subject}_p) VALUES (?,?,?,?)", (adm, score_val, rate, points))
                else:
                    rate = get_grade_4_6_rating(score_val)
                    cursor.execute(f"SELECT 1 FROM {table_name} WHERE adm_no = ?", (adm,))
                    if cursor.fetchone():
                        cursor.execute(f"UPDATE {table_name} SET {subject}_s=?, {subject}_r=? WHERE adm_no=?", (score_val, rate, adm))
                    else:
                        cursor.execute(f"INSERT INTO {table_name} (adm_no, {subject}_s, {subject}_r) VALUES (?,?,?)", (adm, score_val, rate))

                cursor.execute(f"SELECT * FROM {table_name} WHERE adm_no = ?", (adm,))
                row = cursor.fetchone()
                if row:
                    cols = [d[0] for d in cursor.description]
                    data = dict(zip(cols, row))
                    total_s = sum(safe_int(data[c]) for c in cols if c.endswith('_s'))
                    total_p = sum(safe_int(data[c]) for c in cols if c.endswith('_p'))
                    
                    # Count number of subjects (columns ending with _s)
                    num_subjects = len([c for c in cols if c.endswith('_s')])

                    if is_junior:
                        final_lvl = calculate_final_level(total_p, is_primary=False, num_subjects=num_subjects)
                        cursor.execute(f"UPDATE {table_name} SET total_points=?, average_points=? WHERE adm_no=?", (total_p, final_lvl, adm))
                    else:
                        final_lvl = calculate_final_level(total_s, is_primary=True, num_subjects=num_subjects)
                        cursor.execute(f"UPDATE {table_name} SET total_points=?, average_level=? WHERE adm_no=?", (total_s, final_lvl, adm))

        conn.commit()
        return "<body style='background:#020617;color:white;text-align:center;padding:50px;font-family:sans-serif;'><h1>✅ SUCCESS</h1><p>Marks Saved & Totals Updated.</p><a href='/' style='color:#10b981;text-decoration:none;font-weight:bold;'>[ BACK TO PORTAL ]</a></body>"
    except Exception as e:
        return f"<body style='background:maroon;color:white;padding:20px;'><h1>Critical Error: {e}</h1><a href='/'>Go Back</a></body>"
    finally:
        conn.close()

if __name__ == '__main__':
    print(f"!!! SERVER STARTING !!!")
    print(f"!!! WRITING DATA TO: {os.path.abspath(DB_PATH)} !!!")
    app.run(host='0.0.0.0', port=5000, debug=True)