from fsrs import Scheduler, Card, State, Rating, ReviewLog
from operations.db_operations import (
    get_cards_due, get_card_tags, get_card_by_id, update_card_in_db, 
    get_card_review_history_from_db, get_retention_stats_from_db, 
    get_cards_by_tag_from_db, delete_card_from_db, update_card_content_in_db,
    add_card
)
from config import db_path
from pathlib import Path
import datetime
import os
import copy
import uuid

def load_card_content(card_id):
    front_path = Path(db_path + f"/cards/{card_id}_front.md").expanduser()
    back_path = Path(db_path + f"/cards/{card_id}_back.md").expanduser()
    
    front_content = ""
    back_content = ""
    
    if front_path.exists():
        with open(front_path, 'r') as f:
            front_content = f.read()
    
    if back_path.exists():
        with open(back_path, 'r') as f:
            back_content = f.read()
    
    return front_content, back_content

def calculate_next_review_dates(card_id):
    scheduler = Scheduler()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    card = get_card_by_id(card_id)
    if not card:
        return {1: "N/A", 2: "N/A", 3: "N/A", 4: "N/A"}
    
    next_dates = {}
    for rating_value in range(1, 5):
        rating = Rating(rating_value)
        card_copy = copy.deepcopy(card)
        updated_card, _ = scheduler.review_card(card_copy, rating)
        
        if updated_card.due:
            time_diff = updated_card.due - now
            minutes = time_diff.total_seconds() / 60
            hours = minutes / 60
            days = hours / 24
            weeks = days / 7
            
            if minutes < 60:
                next_dates[rating_value] = f"{int(minutes)}min"
            elif hours < 24:
                next_dates[rating_value] = f"{int(hours)}h"
            elif days < 7:
                next_dates[rating_value] = f"{int(days)}d"
            else:
                next_dates[rating_value] = f"{int(weeks)}w"
        else:
            next_dates[rating_value] = "N/A"
    
    return next_dates

def update_card(card_id, card, review_log=None):
    now = datetime.datetime.now(datetime.timezone.utc)
    elapsed_days = 0
    scheduled_days = 0
    
    if card.last_review:
        elapsed_days = (now - card.last_review).days
        if card.due > now:
            scheduled_days = (card.due - now).days
    
    update_card_in_db(
        card_id,
        card.due.isoformat() if card.due else None,
        card.stability,
        card.difficulty,
        elapsed_days,
        scheduled_days,
        card.reps,
        card.lapses,
        str(card.state.value) if card.state else None,
        card.last_review.isoformat() if card.last_review else None,
        review_log
    )

def review_card(card_id, rating_value):
    card = get_card_by_id(card_id)
    
    if not card:
        return None, None
    
    scheduler = Scheduler()
    rating_value = max(1, min(4, rating_value))
    rating = Rating(rating_value)
    
    updated_card, review_log = scheduler.review_card(card, rating)
    update_card(card_id, updated_card, review_log)
    
    return updated_card, review_log

def get_next_card_for_review():
    due_card_ids = get_cards_due()
    
    if not due_card_ids:
        return None, None, None
    
    card_id = due_card_ids[0]
    front_content, back_content = load_card_content(card_id)
    
    return card_id, front_content, back_content

def get_all_cards_due():
    due_card_ids = get_cards_due()
    cards = []
    
    for card_id in due_card_ids:
        front_content, back_content = load_card_content(card_id)
        cards.append({
            "id": card_id,
            "front": front_content,
            "back": back_content
        })
    
    return cards

def filter_due_cards_by_tags(due_cards, selected_tags):
    if not selected_tags:
        return due_cards
    
    filtered_cards = []
    for card in due_cards:
        card_id = card["id"]
        card_tags = get_card_tags(card_id)
        
        if card_tags.intersection(selected_tags):
            filtered_cards.append(card)
    
    return filtered_cards

def get_card_stats(card_id):
    card = get_card_by_id(card_id)
    
    if not card:
        return None
    
    stats = {
        "due": card.due,
        "state": card.state.name if card.state else "Unknown",
        "reps": card.reps,
        "lapses": card.lapses,
        "stability": round(card.stability, 2) if card.stability else 0,
        "difficulty": round(card.difficulty, 2) if card.difficulty else 0,
    }
    
    try:
        stats["retrievability"] = round(card.get_retrievability() * 100, 1)
    except Exception:
        stats["retrievability"] = None
    
    return stats

def get_card_review_history(card_id):
    return get_card_review_history_from_db(card_id)

def get_retention_stats():
    return get_retention_stats_from_db()

def get_cards_by_tag(tag):
    return get_cards_by_tag_from_db(tag)

def get_scheduler_with_custom_parameters(desired_retention=0.9):
    return Scheduler(desired_retention=desired_retention)

def reset_card_progress(card_id):
    new_card = Card()
    
    try:
        update_card(card_id, new_card)
        return True
    except Exception:
        return False

def get_due_count():
    return len(get_cards_due())

def get_review_interface_data():
    card_id, front_content, back_content = get_next_card_for_review()
    
    if not card_id:
        return None
    
    card = get_card_by_id(card_id)
    
    if not card:
        return None
    
    stats = get_card_stats(card_id)
    
    return {
        "id": card_id,
        "front": front_content,
        "back": back_content,
        "stats": stats
    }

def delete_card(card_id):
    result = delete_card_from_db(card_id)
    
    if result:
        front_path = Path(db_path + f"/cards/{card_id}_front.md").expanduser()
        back_path = Path(db_path + f"/cards/{card_id}_back.md").expanduser()
        
        if front_path.exists():
            os.remove(front_path)
        
        if back_path.exists():
            os.remove(back_path)
    
    return result

def update_card_content(card_id, side, content):
    if side not in ["front", "back"]:
        return False
    
    file_path = Path(db_path + f"/cards/{card_id}_{side}.md").expanduser()
    
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"Error updating card content: {e}")
        return False

def duplicate_card(card_id, new_tags=None):
    try:
        front_content, back_content = load_card_content(card_id)
        
        if new_tags is None:
            card_tags = get_card_tags(card_id)
            new_tags = ",".join(card_tags) if card_tags else ""
        
        new_card_id = str(uuid.uuid4())
        
        update_card_content(new_card_id, "front", front_content)
        update_card_content(new_card_id, "back", back_content)
        
        add_card(new_card_id, new_tags)
        
        return new_card_id
    except Exception as e:
        print(f"Error duplicating card: {e}")
        return None

def reset_card_state(card_id):
    try:
        new_card = Card()
        update_card(card_id, new_card)
        return True
    except Exception as e:
        print(f"Error resetting card: {e}")
        return False
