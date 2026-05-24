import sqlite3
import os
# Save it inside the project folder to avoid Windows Permission errors
DB_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "freeman_data.db")

                # Double check if it exists, if not, print where the script THINKs it is
if not os.path.exists(DB_PATH):
 print(f"WARNING: Database not found at {DB_PATH}. Check your username.")

class FreemanDB:
    def __init__(self):
        try:
            self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            # Use a different internal name so it doesn't conflict with the function call
            self._cursor = self.conn.cursor() 
            self.create_table()
            self.create_marksheet_table()
            self.create_playgroup_table()
            self.create_pp1_table()
            self.create_pp2_table()
            self.create_primary_table()
            self.create_settings_table()
            self.create_previous_exams_table()
            self.create_teachers_table()
            self.create_student_reports_table()
            # Temporary fix in database.py
            self.create_marksheet_table() # Ensure this runs at start too
            print(f"DATABASE ACTIVE AT: {DB_PATH}")
        except Exception as e:
            print(f"Desktop Access Denied: {e}. Saving in project folder instead.")
            self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._cursor = self.conn.cursor()

    def cursor(self):
        """This allows self.db.cursor() to work in your other files!"""
        return self.conn.cursor()

    def create_table(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adm_no TEXT UNIQUE, 
                name TEXT,
                grade TEXT,
                gender TEXT,
                phone TEXT
            )
        ''')
        self.conn.commit()

    def add_student(self, adm, name, grade, gender, phone):
        try:
            # We use the internal _cursor here
            self._cursor.execute('''
                INSERT OR REPLACE INTO students (adm_no, name, grade, gender, phone) 
                VALUES (?, ?, ?, ?, ?)
            ''', (adm, name, grade, gender, phone))
            
            self.conn.commit() 
            print(f"Successfully committed {name} to {grade}")
        except Exception as e:
            print(f"Database Error: {e}")
            self.conn.rollback()

    def delete_student(self, adm_no):
        self._cursor.execute("DELETE FROM students WHERE adm_no = ?", (adm_no,))
        self.conn.commit()
        print(f"Student {adm_no} deleted from database.")

    # In database.py (FreemanDB class)
    def create_marksheet_table(self):
        # We only create the core columns. 
        # Subject columns will be added dynamically by the UI/Sync script.
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS marksheet (
                adm_no TEXT PRIMARY KEY,
                total_points INTEGER,
                average_points TEXT, 
                rank INTEGER
            )
        ''')
        self.conn.commit()

    def create_playgroup_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS playgroup_marks (
            adm_no TEXT PRIMARY KEY,
            lang_s INTEGER, lang_r TEXT,
            math_s INTEGER, math_r TEXT,
            env_s INTEGER, env_r TEXT,
            creat_s INTEGER, creat_r TEXT,
            total_points INTEGER,
            average_level TEXT,
            FOREIGN KEY (adm_no) REFERENCES students (adm_no)
        )
        """
        self._cursor.execute(query)
        self.conn.commit()

    def create_pp1_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS pp1_marks (
            adm_no TEXT PRIMARY KEY,
            lang_s INTEGER, lang_r TEXT,
            math_s INTEGER, math_r TEXT,
            env_s INTEGER, env_r TEXT,
            psych_s INTEGER, psych_r TEXT,
            rel_s INTEGER, rel_r TEXT,
            total_points INTEGER,
            average_level TEXT,
            FOREIGN KEY (adm_no) REFERENCES students (adm_no)
        )
        """
        self._cursor.execute(query)
        self.conn.commit()

    def create_pp2_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS pp2_marks (
            adm_no TEXT PRIMARY KEY,
            lang_s INTEGER, lang_r TEXT,
            math_s INTEGER, math_r TEXT,
            env_s INTEGER, env_r TEXT,
            psych_s INTEGER, psych_r TEXT,
            rel_s INTEGER, rel_r TEXT,
            total_points INTEGER,
            average_level TEXT,
            FOREIGN KEY (adm_no) REFERENCES students (adm_no)
        )
        """
        self._cursor.execute(query)
        self.conn.commit()

    def create_primary_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS primary_marks (
            adm_no TEXT PRIMARY KEY,
            eng_s INTEGER, eng_r TEXT,
            kisw_s INTEGER, kisw_r TEXT,
            math_s INTEGER, math_r TEXT,
            scie_s INTEGER, scie_r TEXT,
            agri_s INTEGER, agri_r TEXT,
            sst_s INTEGER, sst_r TEXT,
            cre_s INTEGER, cre_r TEXT,
            ca_s INTEGER, ca_r TEXT,
            phe_s INTEGER, phe_r TEXT,
            total_points INTEGER,
            average_level TEXT,
            rank INTEGER,
            FOREIGN KEY (adm_no) REFERENCES students (adm_no)
        )
        """
        self._cursor.execute(query)
        
        # Add rank column if it doesn't exist (for existing databases)
        try:
            self._cursor.execute("ALTER TABLE primary_marks ADD COLUMN rank INTEGER")
        except:
            pass
        
        self.conn.commit()

    def create_settings_table(self):
        # 1. Create table if it doesn't exist
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS school_settings (
                id INTEGER PRIMARY KEY,
                school_name TEXT
            )
        ''')

        # 2. MANUALLY ADD MISSING COLUMNS (The Fix)
        try:
            self._cursor.execute("ALTER TABLE school_settings ADD COLUMN logo_path TEXT")
            self._cursor.execute("ALTER TABLE school_settings ADD COLUMN sig_path TEXT")
        except:
            # If the columns already exist, this will just skip without crashing
            pass

        # 3. Check for Row 1 and Commit
        self._cursor.execute("SELECT * FROM school_settings WHERE id = 1")
        if not self._cursor.fetchone():
            self._cursor.execute("INSERT INTO school_settings (id, school_name, logo_path, sig_path) VALUES (1, 'NEW SCHOOL', '', '')")
        
        self.conn.commit()

    def create_previous_exams_table(self):
        """Create table to store previous exams with their marks and summary"""
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS previous_exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_name TEXT,
                class_name TEXT,
                exam_date TEXT,
                summary_data TEXT,
                marks_data TEXT,
                UNIQUE(exam_name, class_name)
            )
        ''')
        self.conn.commit()

    def create_teachers_table(self):
        """Create table to store teacher-subject assignments"""
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                teacher_name TEXT NOT NULL,
                teacher_code TEXT NOT NULL,
                UNIQUE(class_name, subject)
            )
        ''')
        self.conn.commit()

    def create_student_reports_table(self):
        """Create table to store student reports for parent portal"""
        self._cursor.execute('''
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
        ''')
        self.conn.commit()

    def save_previous_exam(self, exam_name, class_name, summary_data, marks_data):
        """Save a previous exam with its summary and marks data"""
        import datetime
        exam_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._cursor.execute('''
            INSERT OR REPLACE INTO previous_exams (exam_name, class_name, exam_date, summary_data, marks_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (exam_name, class_name, exam_date, summary_data, marks_data))
        self.conn.commit()

    def get_previous_exams(self, class_name):
        """Get list of previous exams for a class"""
        self._cursor.execute('''
            SELECT exam_name, exam_date FROM previous_exams WHERE class_name = ? ORDER BY exam_date DESC
        ''', (class_name,))
        return self._cursor.fetchall()

    def get_previous_exam_data(self, exam_name, class_name):
        """Get the full data for a specific previous exam"""
        self._cursor.execute('''
            SELECT marks_data, summary_data FROM previous_exams WHERE exam_name = ? AND class_name = ?
        ''', (exam_name, class_name))
        result = self._cursor.fetchone()
        if result:
            return result[0], result[1]  # marks_data, summary_data
        return None, None

    def delete_previous_exam(self, exam_name, class_name):
        """Delete a specific previous exam"""
        self._cursor.execute('''
            DELETE FROM previous_exams WHERE exam_name = ? AND class_name = ?
        ''', (exam_name, class_name))
        self.conn.commit()

    def add_teacher_assignment(self, class_name, subject, teacher_name, teacher_code):
        """Add or update a teacher-subject assignment"""
        self._cursor.execute('''
            INSERT OR REPLACE INTO teachers (class_name, subject, teacher_name, teacher_code)
            VALUES (?, ?, ?, ?)
        ''', (class_name, subject, teacher_name, teacher_code))
        self.conn.commit()
        print(f"Teacher assignment saved: {teacher_name} for {subject} in {class_name}")

    def update_teacher_assignment(self, class_name, old_subject, new_subject, teacher_name, teacher_code):
        """Update a teacher-subject assignment"""
        self._cursor.execute('''
            UPDATE teachers SET subject = ?, teacher_name = ?, teacher_code = ?
            WHERE class_name = ? AND subject = ?
        ''', (new_subject, teacher_name, teacher_code, class_name, old_subject))
        self.conn.commit()
        print(f"Teacher assignment updated: {teacher_name} for {new_subject} in {class_name}")

    def delete_teacher_assignment(self, class_name, subject):
        """Delete a teacher-subject assignment"""
        self._cursor.execute('''
            DELETE FROM teachers WHERE class_name = ? AND subject = ?
        ''', (class_name, subject))
        self.conn.commit()
        print(f"Teacher assignment deleted for {subject} in {class_name}")

    def get_teacher_assignments(self, class_name):
        """Get all teacher assignments for a class"""
        self._cursor.execute('''
            SELECT subject, teacher_name, teacher_code FROM teachers WHERE class_name = ?
        ''', (class_name,))
        return self._cursor.fetchall()

    def get_all_teachers(self):
        """Get all teacher assignments for sync to cloud"""
        self._cursor.execute('''
            SELECT class_name, subject, teacher_name, teacher_code FROM teachers
        ''')
        return self._cursor.fetchall()

    def verify_teacher_code(self, teacher_name, teacher_code, class_name, subject):
        """Verify if a teacher's code matches for a specific subject"""
        self._cursor.execute('''
            SELECT teacher_code FROM teachers 
            WHERE class_name = ? AND subject = ? AND teacher_name = ?
        ''', (class_name, subject, teacher_name))
        result = self._cursor.fetchone()
        if result and result[0] == teacher_code:
            return True
        return False