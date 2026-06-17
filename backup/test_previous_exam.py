import sqlite3
import json

conn = sqlite3.connect('freeman_data.db')
cursor = conn.cursor()

# Get previous exam data
cursor.execute('SELECT marks_data FROM previous_exams WHERE exam_name = ? AND class_name = ?', ('PERFORMANCE RECORD', 'Grade 9'))
result = cursor.fetchone()

if result:
    marks_data = json.loads(result[0])
    print(f"Previous exam data: {marks_data}")
    
    # Parse the data
    if marks_data and len(marks_data) > 0:
        student_record = marks_data[0]
        print(f"\nStudent record: {student_record}")
        
        # Junior format: [name, score1, rating1, points1, score2, rating2, points2, ...]
        subjects = ["MATH", "ENG", "KISW", "INT SCIE", "PRE-TECH", "SST", "CRE", "AGRI", "C/A"]
        marks_list = student_record[1:]  # Skip name
        
        print(f"\nMarks list: {marks_list}")
        print(f"Number of subjects: {len(subjects)}")
        print(f"Expected values: {len(subjects) * 3}")
        print(f"Actual values: {len(marks_list)}")
        
        # Extract marks for each subject
        for i, subject in enumerate(subjects):
            if i * 3 + 2 < len(marks_list):
                score = marks_list[i * 3]
                rating = marks_list[i * 3 + 1]
                points = marks_list[i * 3 + 2]
                print(f"{subject}: score={score}, rating={rating}, points={points}")
            else:
                print(f"{subject}: Not enough data (need index {i * 3 + 2}, have {len(marks_list)})")

conn.close()
