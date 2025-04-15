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
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    current_time = datetime.datetime.now().isoformat()
    c.execute("SELECT command FROM schedulling WHERE due <= ?", (current_time,))
    cards = c.fetchall()
    conn.close()
    return [card[0] for card in cards]

def get_card_tags(card_id):
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    c.execute("SELECT tags FROM schedulling WHERE command = ?", (card_id,))
    result = c.fetchone()
    conn.close()
    
    if result and result[0]:
        return set(tag.strip() for tag in result[0].split(',') if tag.strip())
    
    return set()

def update_card_tags(card_id, tags):
    try:
        tags_str = ','.join(tags)
        
        conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
        c = conn.cursor()
        c.execute("UPDATE schedulling SET tags = ? WHERE command = ?", (tags_str, card_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating card tags: {e}")
        return False

def get_cards_by_tag_from_db(tag):
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    c.execute("""
        SELECT command FROM schedulling
        WHERE tags LIKE ? OR tags LIKE ? OR tags LIKE ? OR tags = ?
    """, (
        f"{tag},%",  # Tag at the beginning
        f"%,{tag},%",  # Tag in the middle
        f"%,{tag}",  # Tag at the end
        tag  # Tag is the only tag
    ))
    
    card_ids = c.fetchall()
    conn.close()
    
    return [card_id[0] for card_id in card_ids]

def get_cards_due_for_tags(tags):
    all_tags = set(get_tags())
    
    if not tags or tags == all_tags:
        return get_cards_due()
    
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    
    current_time = datetime.datetime.now().isoformat()
    c.execute("SELECT command FROM schedulling WHERE due <= ?", (current_time,))
    due_cards = [card[0] for card in c.fetchall()]
    conn.close()
    
    filtered_cards = []
    for card_id in due_cards:
        card_tags = get_card_tags(card_id)
        if any(tag in tags for tag in card_tags):
            filtered_cards.append(card_id)
    
    return filtered_cards

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

def get_tag_due_counts():
    tags = get_tags()
    tag_counts = {tag: 0 for tag in tags}
    
    due_cards = get_cards_due()
    
    for card_id in due_cards:
        card_tags = get_card_tags(card_id)
        for tag in card_tags:
            tag = tag.strip()
            if tag in tag_counts:
                tag_counts[tag] += 1
    
    return tag_counts

def update_card_rating(card_id, rating):
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    
    c.execute("""
        SELECT stability, difficulty, state, reps, lapses
        FROM schedulling
        WHERE command = ?
    """, (card_id,))
    
    result = c.fetchone()
    if not result:
        conn.close()
        return False
    
    stability, difficulty, state, reps, lapses = result
    
    scheduler = Scheduler()
    card = Card(
        stability=stability, 
        difficulty=difficulty,
        state=state,
        reps=reps,
        lapses=lapses
    )
    
    rating_map = {
        'again': Rating.AGAIN,
        'hard': Rating.HARD,
        'good': Rating.GOOD,
        'easy': Rating.EASY
    }
    rating_obj = rating_map.get(rating.lower(), Rating.GOOD)
    
    now = datetime.datetime.now()
    review_log, card = scheduler.review(card, rating_obj, now)
    
    c.execute("""
        UPDATE schedulling
        SET stability = ?, difficulty = ?, state = ?, due = ?, 
            reps = ?, lapses = ?, last_review = ?
        WHERE command = ?
    """, (
        card.stability,
        card.difficulty,
        card.state,
        card.due,
        card.reps,
        card.lapses,
        now.isoformat(),
        card_id
    ))
    
    c.execute("""
        INSERT INTO review_log (card_id, rating, review_date)
        VALUES (?, ?, ?)
    """, (
        card_id,
        rating.lower(),
        now.isoformat()
    ))
    
    conn.commit()
    conn.close()
    return True

def get_card_by_id(card_id):
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    c.execute("""
        SELECT due, stability, difficulty, elapsed_days, 
               scheduled_days, reps, lapses, state, last_review
        FROM schedulling
        WHERE command = ?
    """, (card_id,))
    
    result = c.fetchone()
    conn.close()
    
    if not result:
        return None
    
    card = Card()
    
    if result[0]:  # due
        try:
            card.due = datetime.datetime.fromisoformat(result[0])
        except (ValueError, TypeError):
            card.due = datetime.datetime.now(datetime.timezone.utc)
    
    if result[1] is not None:  # stability
        try:
            card.stability = float(result[1])
        except (ValueError, TypeError):
            pass
    
    if result[2] is not None:  # difficulty
        try:
            card.difficulty = float(result[2])
        except (ValueError, TypeError):
            pass
    
    if result[5] is not None:  # reps
        try:
            card.reps = int(result[5])
        except (ValueError, TypeError):
            pass
    
    if result[6] is not None:  # lapses
        try:
            card.lapses = int(result[6])
        except (ValueError, TypeError):
            pass
    
    if result[7]:  # state
        try:
            card.state = State(int(result[7]))
        except (ValueError, TypeError):
            pass
    
    if result[8]:  # last_review
        try:
            card.last_review = datetime.datetime.fromisoformat(result[8])
        except (ValueError, TypeError):
            pass
    
    return card

def update_card_in_db(card_id, due, stability, difficulty, elapsed_days, scheduled_days, 
                      reps, lapses, state, last_review, review_log=None):
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    
    c.execute("""
        UPDATE schedulling
        SET due = ?, stability = ?, difficulty = ?, 
            elapsed_days = ?, scheduled_days = ?, reps = ?, 
            lapses = ?, state = ?, last_review = ?
        WHERE command = ?
    """, (
        due,
        stability,
        difficulty,
        elapsed_days,
        scheduled_days,
        reps,
        lapses,
        state,
        last_review,
        card_id
    ))
    
    if review_log:
        c.execute("""
            INSERT INTO review_log (card_id, rating, review_date)
            VALUES (?, ?, ?)
        """, (
            card_id,
            str(review_log.rating.value),
            review_log.review_datetime.isoformat()
        ))
    
    conn.commit()
    conn.close()

def get_card_review_history_from_db(card_id):
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    c.execute("""
        SELECT rating, review_date
        FROM review_log
        WHERE card_id = ?
        ORDER BY review_date
    """, (card_id,))
    
    results = c.fetchall()
    conn.close()
    
    history = []
    for result in results:
        try:
            rating = int(result[0])
            review_date = datetime.datetime.fromisoformat(result[1])
            
            rating_names = {
                1: "Again",
                2: "Hard",
                3: "Good",
                4: "Easy"
            }
            
            history.append({
                "rating": rating,
                "rating_name": rating_names.get(rating, "Unknown"),
                "review_date": review_date
            })
        except (ValueError, TypeError):
            continue
    
    return history

def get_retention_stats_from_db():
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM review_log")
    total_reviews = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM review_log WHERE rating = '1'")
    again_ratings = c.fetchone()[0] or 0
    
    retention_rate = 0
    if total_reviews > 0:
        retention_rate = (total_reviews - again_ratings) / total_reviews
    
    c.execute("SELECT AVG(CAST(rating AS REAL)) FROM review_log")
    avg_rating_result = c.fetchone()[0]
    avg_rating = avg_rating_result if avg_rating_result is not None else 0
    
    c.execute("SELECT rating, COUNT(*) FROM review_log GROUP BY rating")
    rating_counts = {int(r[0]): r[1] for r in c.fetchall()}
    
    conn.close()
    
    return {
        "total_reviews": total_reviews,
        "again_ratings": again_ratings,
        "retention_rate": round(retention_rate * 100, 1),
        "avg_rating": round(avg_rating, 2),
        "rating_counts": {
            "Again": rating_counts.get(1, 0),
            "Hard": rating_counts.get(2, 0),
            "Good": rating_counts.get(3, 0),
            "Easy": rating_counts.get(4, 0)
        }
    }

def delete_card_from_db(card_id):
    try:
        conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
        c = conn.cursor()
        
        c.execute("DELETE FROM schedulling WHERE command = ?", (card_id,))
        c.execute("DELETE FROM review_log WHERE card_id = ?", (card_id,))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error deleting card from DB: {e}")
        return False

def update_card_content_in_db(card_id, side, content):
    try:
        file_path = Path(db_path + f"/cards/{card_id}_{side}.md").expanduser()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"Error updating card content in DB: {e}")
        return False
