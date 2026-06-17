import sqlite3

conn = sqlite3.connect('freeman_data.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%MOCK%'")
tables = cursor.fetchall()
print(f"Tables with MOCK: {tables}")

if tables:
    table_name = tables[0][0]
    print(f"\nTable: {table_name}")
    
    # Get table structure
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    print(f"\nTable structure:\n{cursor.fetchone()[0]}")
    
    # Get sample data
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
    columns = [description[0] for description in cursor.description]
    print(f"\nColumns: {columns}")
    
    row = cursor.fetchone()
    if row:
        print(f"\nSample row (first 20 values): {row[:20]}")

conn.close()
