from common.common_db import get_connection

conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT name FROM sys.databases")
for row in cursor.fetchall():
    print(row[0])
conn.close()