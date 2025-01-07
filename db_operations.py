from config import db_path 
import sqlite3
from pathlib import Path


schema = """
CREATE TABLE IF NOT EXISTS schedulling (id integer primary key,priority integer,due text,  stability real, difficulty real, elapsed_days integer, scheduled_days integer, reps integer, lapses integer, state text, last_review text, command text);
"""

def create_db():
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    c.execute(schema)
    conn.commit()
    conn.close()

