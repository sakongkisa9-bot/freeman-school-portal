import sqlite3

conn = sqlite3.connect('freeman_data.db')
cursor = conn.cursor()

# Get all tables
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()

print('Tables in database:')
for table in tables:
    print(f"  - {table[0]}")

# Check for Grade 9 tables
print('\nTables containing "Grade 9":')
for table in tables:
    if 'Grade 9' in table[0] or 'grade9' in table[0].lower():
        print(f"  - {table[0]}")

# Check for marks tables
print('\nTables containing "marks":')
for table in tables:
    if 'mark' in table[0].lower():
        print(f"  - {table[0]}")

conn.close()
