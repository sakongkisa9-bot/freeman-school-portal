import sqlite3

conn = sqlite3.connect('freeman_data.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("Tables:", tables)

# Check for JESMA table
jesma_tables = [t for t in tables if 'jesma' in t.lower()]
print("JESMA tables:", jesma_tables)

# Check for marks tables
marks_tables = [t for t in tables if 'marks' in t.lower()]
print("Marks tables:", marks_tables)

# If JESMA table exists, check James Wafula's marks
if jesma_tables:
    for table in jesma_tables:
        print(f"\nChecking {table}:")
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        print("Columns:", columns)
        
        cursor.execute(f"SELECT * FROM {table} WHERE student_name LIKE '%James%' OR adm_no = '020'")
        rows = cursor.fetchall()
        print(f"Rows for James Wafula: {len(rows)}")
        if rows:
            print("First row:", rows[0])

conn.close()
