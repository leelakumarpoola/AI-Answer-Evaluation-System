from app.database import engine
from sqlalchemy import text

with engine.connect() as c:
    r = c.execute(text('SELECT password_hash FROM students WHERE id = 1')).fetchone()
    print('Student hash exists:', bool(r[0]))
    r = c.execute(text('SELECT password_hash FROM professors WHERE id = 1')).fetchone()
    print('Professor hash exists:', bool(r[0]))
