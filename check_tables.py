from database import FreemanDB
db = FreemanDB()
db._cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = db._cursor.fetchall()
print("Tables:", [t[0] for t in tables])
