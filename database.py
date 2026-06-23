import sqlite3
import os
import sys

# Handle both development and executable environments
if getattr(sys, 'frozen', False):
    # Running as executable
    BASE_DIR = sys._MEIPASS
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))

# For executable, use user data directory for database
if getattr(sys, 'frozen', False):
    import tempfile
    USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    DB_PATH = os.path.join(USER_DATA_DIR, "freeman_data.db")
    print(f"[EXECUTABLE MODE] Database path: {DB_PATH}")
else:
    # Save it inside the project folder for development
    DB_PATH = os.path.join(BASE_DIR, "freeman_data.db")
    print(f"[DEV MODE] Database path: {DB_PATH}")

# Double check if it exists, if not, print where the script THINKs it is
if not os.path.exists(DB_PATH):
    print(f"WARNING: Database not found at {DB_PATH}. A new one will be created.")

class FreemanDB:
    def __init__(self):
        try:
            self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            # Use a different internal name so it doesn't conflict with the function call
            self._cursor = self.conn.cursor()
            print(f"DATABASE ACTIVE AT: {DB_PATH}")
            print(f"DATABASE CONNECTION ID: {id(self.conn)}")
            # Check if database has data
            self._cursor.execute("SELECT COUNT(*) FROM students")
            count = self._cursor.fetchone()[0]
            print(f"DATABASE STUDENT COUNT ON INIT: {count}")
        except Exception as e:
            print(f"Desktop Access Denied: {e}. Saving in project folder instead.")
            self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._cursor = self.conn.cursor()
            print(f"DATABASE CONNECTION ID: {id(self.conn)}")
        
        # Create all tables (run regardless of connection success)
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
        self.create_payment_tracking_table()
        self.create_license_status_table()
        self.create_deleted_students_footprint_table()
        self.create_alert_queue_table()
        
        # Run database migrations
        self.run_migrations()

    def run_migrations(self):
        """Run database migrations to handle schema changes"""
        try:
            # Create migrations table if it doesn't exist
            self._cursor.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
            
            # Get all applied migration versions
            self._cursor.execute('SELECT version FROM schema_migrations ORDER BY applied_at DESC')
            applied_versions = set(row[0] for row in self._cursor.fetchall())
            
            # Define migrations
            migrations = [
                ("1.0.0", self.migration_1_0_0),
                ("1.0.1", self.migration_1_0_1),
            ]
            
            # Run pending migrations
            for version, migration_func in migrations:
                if version not in applied_versions:
                    print(f"Running migration to version {version}")
                    migration_func()
                    self._cursor.execute('INSERT INTO schema_migrations (version) VALUES (?)', (version,))
                    self.conn.commit()
                    print(f"Migration to version {version} completed")
                    
        except Exception as e:
            print(f"Error running migrations: {e}")
    
    def _compare_versions(self, v1, v2):
        """Compare two version strings"""
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1_val = v1_parts[i] if i < len(v1_parts) else 0
            v2_val = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1_val > v2_val:
                return 1
            elif v1_val < v2_val:
                return -1
        
        return 0
    
    def migration_1_0_0(self):
        """Initial migration - baseline schema"""
        # This is the baseline, no changes needed
        pass
    
    def migration_1_0_1(self):
        """Migration for version 1.0.1 - add any new columns or tables"""
        # Example: Add new column if it doesn't exist
        try:
            self._cursor.execute("ALTER TABLE students ADD COLUMN stream TEXT")
            self.conn.commit()
        except:
            pass  # Column might already exist

    def cursor(self):
        """This allows self.db.cursor() to work in your other files!"""
        # Return the internal cursor to avoid creating new cursors that might not see committed data
        return self._cursor

    def create_table(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adm_no TEXT UNIQUE, 
                name TEXT,
                grade TEXT,
                gender TEXT,
                phone TEXT,
                photo TEXT,
                stream TEXT
            )
        ''')
        # Add photo column if it doesn't exist (for existing databases)
        try:
            self._cursor.execute("ALTER TABLE students ADD COLUMN photo TEXT")
            self.conn.commit()
        except:
            pass
        # Add stream column if it doesn't exist (for existing databases)
        try:
            self._cursor.execute("ALTER TABLE students ADD COLUMN stream TEXT")
            self.conn.commit()
        except:
            pass
        self.conn.commit()

    def add_student(self, adm, name, grade, gender, phone, photo=None, stream=None, check_footprint=True):
        """Add student with optional footprint check for anti-cheating"""
        try:
            # Get school name for alert
            school_name = "Unknown School"
            try:
                import json
                # Use BASE_DIR from module level
                config_path = os.path.join(BASE_DIR, "school_config.json")
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = json.load(f)
                        school_name = config.get("school_name", "Unknown School")
            except Exception:
                pass
            
            # Check for deleted student footprint if enabled
            if check_footprint:
                footprint = self.check_student_footprint(name, adm)
                if footprint:
                    # Student was previously deleted - queue alert with school name
                    message = f"⚠️ CHEATING ALERT [{school_name}]: Student '{name}' (ADM: {adm}) was previously deleted on {footprint[5]} and is now being re-added!"
                    self.queue_alert("student_readdition", message, name, adm)
                    print(f"FOOTPRINT ALERT: {message}")
                    
                    # Try to send alert immediately
                    try:
                        from notification_service import NotificationService
                        from datetime import datetime
                        ns = NotificationService()
                        results = ns.send_alert(message)
                        sent_successfully = any(result[1] for result in results)
                        if sent_successfully:
                            # Mark the alert as sent
                            self._cursor.execute('UPDATE alert_queue SET status = "sent", sent_at = ? WHERE status = "pending" ORDER BY id DESC LIMIT 1', 
                                                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
                            self.conn.commit()
                            print("Alert sent successfully to Telegram")
                        else:
                            print("Alert queued (will retry on startup) - Telegram timeout")
                    except Exception as e:
                        print(f"Alert queued (will retry on startup) - Error: {e}")
            
            # Use public cursor method for consistency
            self._cursor.execute('''
                INSERT OR REPLACE INTO students (adm_no, name, grade, gender, phone, photo, stream)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (adm, name, grade, gender, phone, photo, stream or "None"))

            self.conn.commit()
            print(f"Successfully committed {name} to {grade} (Database: {DB_PATH})")
            return True
        except Exception as e:
            print(f"Database Error: {e}")
            self.conn.rollback()
            return False

    def delete_student(self, adm_no, record_footprint=True):
        """Delete student and optionally record in footprint for anti-cheating"""
        # Get student info before deletion for footprint
        if record_footprint:
            self._cursor.execute("SELECT name, grade FROM students WHERE adm_no = ?", (adm_no,))
            student = self._cursor.fetchone()
            if student:
                self.record_student_deletion(student[0], adm_no, student[1])
                print(f"Student {adm_no} footprint recorded for anti-cheating.")
        
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

    def create_payment_tracking_table(self):
        """Create table to track payments and license status"""
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                merchant_request_id TEXT,
                checkout_request_id TEXT,
                mpesa_receipt TEXT,
                transaction_date TEXT,
                result_code INTEGER,
                result_desc TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def create_license_status_table(self):
        """Create table to track license status and expiry"""
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS license_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                installation_fee_paid INTEGER DEFAULT 0,
                trial_started INTEGER DEFAULT 0,
                premium_started INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def save_payment(self, payment_type, amount, merchant_request_id=None, checkout_request_id=None, 
                    mpesa_receipt=None, transaction_date=None, result_code=None, result_desc=None, status='pending'):
        """Save a payment record"""
        self._cursor.execute('''
            INSERT INTO payment_tracking 
            (payment_type, amount, status, merchant_request_id, checkout_request_id, mpesa_receipt, 
             transaction_date, result_code, result_desc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (payment_type, amount, status, merchant_request_id, checkout_request_id, mpesa_receipt,
              transaction_date, result_code, result_desc))
        self.conn.commit()

    def update_payment_status(self, payment_id, status, mpesa_receipt=None, result_code=None, result_desc=None):
        """Update payment status"""
        self._cursor.execute('''
            UPDATE payment_tracking 
            SET status = ?, mpesa_receipt = ?, result_code = ?, result_desc = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, mpesa_receipt, result_code, result_desc, payment_id))
        self.conn.commit()

    def get_license_status(self):
        """Get current license status"""
        self._cursor.execute('SELECT * FROM license_status ORDER BY id DESC LIMIT 1')
        return self._cursor.fetchone()

    def save_license_status(self, license_type, start_date, end_date, installation_fee_paid=0, trial_started=0, premium_started=0):
        """Save or update license status"""
        # Check if there's an existing active license
        existing = self.get_license_status()
        if existing:
            self._cursor.execute('''
                UPDATE license_status 
                SET license_type = ?, start_date = ?, end_date = ?, installation_fee_paid = ?, 
                    trial_started = ?, premium_started = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (license_type, start_date, end_date, installation_fee_paid, trial_started, premium_started, existing[0]))
        else:
            self._cursor.execute('''
                INSERT INTO license_status 
                (license_type, start_date, end_date, installation_fee_paid, trial_started, premium_started)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (license_type, start_date, end_date, installation_fee_paid, trial_started, premium_started))
        self.conn.commit()

    def get_total_students(self):
        """Get total number of students in the system"""
        self._cursor.execute('SELECT COUNT(*) FROM students')
        result = self._cursor.fetchone()
        return result[0] if result else 0

    def initialize_license_status(self, grace_period_days):
        """Initialize license status with grace period"""
        from datetime import datetime, timedelta
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=grace_period_days)
        
        self.save_license_status(
            license_type="grace_period",
            start_date=start_date.strftime("%Y-%m-%d %H:%M:%S"),
            end_date=end_date.strftime("%Y-%m-%d %H:%M:%S"),
            installation_fee_paid=0,
            trial_started=0,
            premium_started=0
        )

    def create_deleted_students_footprint_table(self):
        """Create table to track deleted students for anti-cheating"""
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS deleted_students_footprint (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                adm_no TEXT NOT NULL,
                grade TEXT,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                alert_sent INTEGER DEFAULT 0,
                alert_sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def create_alert_queue_table(self):
        """Create table to queue alerts for offline scenarios"""
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                message TEXT NOT NULL,
                student_name TEXT,
                adm_no TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        self.conn.commit()

    def record_student_deletion(self, student_name, adm_no, grade):
        """Record student deletion in footprint table"""
        from datetime import datetime, timedelta
        
        deleted_at = datetime.now()
        expires_at = deleted_at + timedelta(days=365)  # 365 days retention
        
        self._cursor.execute('''
            INSERT INTO deleted_students_footprint 
            (student_name, adm_no, grade, deleted_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (student_name, adm_no, grade, deleted_at.strftime("%Y-%m-%d %H:%M:%S"), expires_at.strftime("%Y-%m-%d %H:%M:%S")))
        self.conn.commit()

    def check_student_footprint(self, student_name, adm_no):
        """Check if student was previously deleted within 365 days"""
        from datetime import datetime
        
        self._cursor.execute('''
            SELECT * FROM deleted_students_footprint 
            WHERE student_name = ? AND adm_no = ? AND expires_at > ?
            ORDER BY deleted_at DESC LIMIT 1
        ''', (student_name, adm_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        return self._cursor.fetchone()

    def queue_alert(self, alert_type, message, student_name=None, adm_no=None):
        """Queue an alert for offline scenarios"""
        self._cursor.execute('''
            INSERT INTO alert_queue 
            (alert_type, message, student_name, adm_no, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (alert_type, message, student_name, adm_no))
        self.conn.commit()

    def get_pending_alerts(self, max_age_hours=72):
        """Get pending alerts older than specified hours"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        self._cursor.execute('''
            SELECT * FROM alert_queue 
            WHERE status = 'pending' AND created_at < ?
            ORDER BY created_at ASC
        ''', (cutoff_time.strftime("%Y-%m-%d %H:%M:%S"),))
        return self._cursor.fetchall()

    def get_all_pending_alerts(self):
        """Get all pending alerts regardless of age"""
        self._cursor.execute('''
            SELECT * FROM alert_queue 
            WHERE status = 'pending'
            ORDER BY created_at ASC
        ''')
        return self._cursor.fetchall()

    def mark_alert_sent(self, alert_id):
        """Mark an alert as sent"""
        from datetime import datetime
        self._cursor.execute('''
            UPDATE alert_queue 
            SET status = 'sent', sent_at = ?
            WHERE id = ?
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), alert_id))
        self.conn.commit()

    def cleanup_expired_footprints(self):
        """Remove footprints that have expired (older than 365 days)"""
        from datetime import datetime
        self._cursor.execute('''
            DELETE FROM deleted_students_footprint 
            WHERE expires_at < ?
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
        self.conn.commit()