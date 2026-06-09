import sqlite3

conn = sqlite3.connect('freeman_data.db')
cursor = conn.cursor()

# Get columns in marksheet table
cursor.execute('PRAGMA table_info(marksheet)')
columns = cursor.fetchall()

print('Columns in marksheet table:')
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# Check for intscie and pre-tech columns
print('\nColumns containing "int" or "pre":')
for col in columns:
    col_name = col[1].lower()
    if 'int' in col_name or 'pre' in col_name:
        print(f"  - {col[1]}")

# Get a sample row
print('\nSample row from marksheet for Grade 9:')
cursor.execute('SELECT * FROM marksheet WHERE class_name = ? LIMIT 1', ('Grade 9',))
result = cursor.fetchone()
if result:
    print(f"  First 20 columns: {result[:20]}")
else:
    print('  No data found for Grade 9')

conn.close()
