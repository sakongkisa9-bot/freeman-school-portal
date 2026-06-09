import sqlite3

# Connect to the cloud database
conn = sqlite3.connect('freeman_data.db')
cursor = conn.cursor()

# Check the marks table for Grade 9 with PERFORMANCE REC exam
print("Checking marks table for PERFORMANCE REC exam:")
cursor.execute('''
    SELECT adm_no, student_name, exam_title, total_points, average_level, subject_scores_json
    FROM marks
    WHERE grade = 'Grade 9' AND exam_title = 'PERFORMANCE REC'
    LIMIT 1
''')
row = cursor.fetchone()

if row:
    print(f"adm_no: {row[0]}")
    print(f"student_name: {row[1]}")
    print(f"exam_title: {row[2]}")
    print(f"total_points: {row[3]}")
    print(f"average_level: {row[4]}")
    print(f"subject_scores_json (first 500 chars): {row[5][:500] if row[5] else None}")
else:
    print("No PERFORMANCE REC exam found in marks table")

# Also check for current exam
print("\nChecking marks table for current exam:")
cursor.execute('''
    SELECT adm_no, student_name, exam_title, total_points, average_level, subject_scores_json
    FROM marks
    WHERE grade = 'Grade 9' AND exam_title != 'PERFORMANCE REC'
    LIMIT 1
''')
row = cursor.fetchone()

if row:
    print(f"adm_no: {row[0]}")
    print(f"student_name: {row[1]}")
    print(f"exam_title: {row[2]}")
    print(f"total_points: {row[3]}")
    print(f"average_level: {row[4]}")
    print(f"subject_scores_json (first 500 chars): {row[5][:500] if row[5] else None}")
else:
    print("No current exam found in marks table")

conn.close()
