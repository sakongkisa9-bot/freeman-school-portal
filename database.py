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
            self.create_primary_table()   # Add this new one!
            self.create_settings_table()
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
            FOREIGN KEY (adm_no) REFERENCES students (adm_no)
        )
        """
        self._cursor.execute(query)
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