import sqlite3

conn = sqlite3.connect('freeman_data.db')
cursor = conn.cursor()

# Check previous_exams table structure
cursor.execute("PRAGMA table_info(previous_exams)")
columns = [row[1] for row in cursor.fetchall()]
print("previous_exams columns:", columns)

# Get all previous exams
cursor.execute("SELECT * FROM previous_exams")
rows = cursor.fetchall()
print(f"\nTotal previous exams: {len(rows)}")

# Show all exams
for row in rows:
    print(row)

# Check for JESMA exam
cursor.execute("SELECT * FROM previous_exams WHERE exam_name = 'JESMA'")
jesma_rows = cursor.fetchall()
print(f"\nJESMA exams: {len(jesma_rows)}")
for row in jesma_rows:
    print(row)

# Check for MOCK exam
cursor.execute("SELECT * FROM previous_exams WHERE exam_name = 'MOCK'")
mock_rows = cursor.fetchall()
print(f"\nMOCK exams: {len(mock_rows)}")
for row in mock_rows:
    print(row)

conn.close()
