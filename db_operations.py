from config import db_path 
from pathlib import Path
import sqlite3
from fsrs import Scheduler, Card, State, Rating, ReviewLog
import datetime

schema = ["""
CREATE TABLE IF NOT EXISTS schedulling (
    id integer primary key autoincrement,
    priority integer,
    due text,
    stability real,
    difficulty real,
    elapsed_days integer,
    scheduled_days integer,
    reps integer,
    lapses integer,
    state text,
    last_review text,
    command text,
    tags text
);""",
"""
CREATE TABLE IF NOT EXISTS review_log (
    id integer primary key,
    card_id integer,
    rating text,
    review_date text
);""",
"""
CREATE TABLE IF NOT EXISTS tags (
    id integer primary key autoincrement,
    tag text
);"""]


def create_db():
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    for query in schema:
        c.execute(query)
    conn.commit()
    conn.close()

def add_card(command, tags):
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    card = Card()
    conn.execute("INSERT INTO schedulling (priority, due, stability, difficulty, elapsed_days, scheduled_days, reps, lapses, state, last_review, command, tags) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (1, card.due, card.stability, card.difficulty, 0, 0, 0, 0, card.state, card.last_review, command, tags))
    conn.commit()
    conn.close()

def get_cards_due():
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    c.execute("SELECT command FROM schedulling WHERE due <= ?", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    cards = c.fetchall()
    conn.close()
    return [card[0] for card in cards]

def new_tag(text):
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    conn.execute("INSERT INTO tags (tag) VALUES (?)", (text,))
    conn.commit()
    conn.close()

def get_tags():
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    c.execute("SELECT tag FROM tags")
    tags = c.fetchall()
    conn.close()
    return [tag[0] for tag in tags]



