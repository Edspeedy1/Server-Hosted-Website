import sqlite3


conn = sqlite3.connect('chatroom-database.db')
c = conn.cursor()

c.execute('''DROP TABLE sqlite_sequence''')

conn.commit()
conn.close()
