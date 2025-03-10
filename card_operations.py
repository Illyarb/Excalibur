from fsrs import Scheduler, Card, State, Rating, ReviewLog
from db_operations import get_cards_due
from config import db_path
from pathlib import Path
import sqlite3
import datetime
import os

def load_card_content(card_id):
    """
    Load the front and back content of a card.
    
    Args:
        card_id (str): The ID of the card to load.
        
    Returns:
        tuple: (front_content, back_content) as strings.
    """
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

def get_card_by_id(card_id):
    """
    Retrieve a card's scheduling information from the database.
    
    Args:
        card_id (str): The ID of the card to retrieve.
        
    Returns:
        Card: An FSRS Card object with the card's scheduling information, or None if not found.
    """
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
    
    # Create a Card object with the retrieved data
    card = Card()
    
    # Parse values from the database
    if result[0]:  # due
        try:
            card.due = datetime.datetime.fromisoformat(result[0])
        except (ValueError, TypeError):
            # If the date can't be parsed, use the current time
            card.due = datetime.datetime.now(datetime.timezone.utc)
    
    if result[1] is not None:  # stability
        try:
            card.stability = float(result[1])
        except (ValueError, TypeError):
            pass  # Use default value
    
    if result[2] is not None:  # difficulty
        try:
            card.difficulty = float(result[2])
        except (ValueError, TypeError):
            pass  # Use default value
    
    if result[5] is not None:  # reps
        try:
            card.reps = int(result[5])
        except (ValueError, TypeError):
            pass  # Use default value
    
    if result[6] is not None:  # lapses
        try:
            card.lapses = int(result[6])
        except (ValueError, TypeError):
            pass  # Use default value
    
    if result[7]:  # state
        try:
            card.state = State(int(result[7]))
        except (ValueError, TypeError):
            pass  # Use default value
    
    if result[8]:  # last_review
        try:
            card.last_review = datetime.datetime.fromisoformat(result[8])
        except (ValueError, TypeError):
            # If the date can't be parsed, use None
            pass
    
    return card

def update_card(card_id, card, review_log=None):
    """
    Update a card's scheduling information in the database.
    
    Args:
        card_id (str): The ID of the card to update.
        card (Card): The FSRS Card object with updated scheduling information.
        review_log (ReviewLog, optional): The FSRS ReviewLog object to store if provided.
    """
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    
    # Calculate elapsed_days and scheduled_days
    elapsed_days = 0
    scheduled_days = 0
    
    if card.last_review:
        now = datetime.datetime.now(datetime.timezone.utc)
        elapsed_days = (now - card.last_review).days
        
        if card.due > now:
            scheduled_days = (card.due - now).days
    
    # Update the card in the database
    c.execute("""
        UPDATE schedulling
        SET due = ?, stability = ?, difficulty = ?, 
            elapsed_days = ?, scheduled_days = ?, reps = ?, 
            lapses = ?, state = ?, last_review = ?
        WHERE command = ?
    """, (
        card.due.isoformat() if card.due else None,
        card.stability,
        card.difficulty,
        elapsed_days,
        scheduled_days,
        card.reps,
        card.lapses,
        str(card.state.value) if card.state else None,
        card.last_review.isoformat() if card.last_review else None,
        card_id
    ))
    
    # If review_log is provided, add it to the review_log table
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

def review_card(card_id, rating_value):
    """
    Review a card with the given rating.
    
    Args:
        card_id (str): The ID of the card to review.
        rating_value (int): The rating value (1-4).
        
    Returns:
        tuple: (updated_card, review_log) or (None, None) if the card is not found.
    """
    # Load the card from the database
    card = get_card_by_id(card_id)
    
    if not card:
        return None, None
    
    # Initialize the FSRS scheduler
    scheduler = Scheduler()
    
    # Convert the rating value (1-4) to a Rating enum
    # Ensure rating_value is within valid range
    rating_value = max(1, min(4, rating_value))
    rating = Rating(rating_value)
    
    # Review the card
    updated_card, review_log = scheduler.review_card(card, rating)
    
    # Update the card in the database
    update_card(card_id, updated_card, review_log)
    
    return updated_card, review_log

def get_next_card_for_review():
    """
    Get the next card that is due for review.
    
    Returns:
        tuple: (card_id, front_content, back_content) or (None, None, None) if no cards are due.
    """
    # Get card IDs that are due
    due_card_ids = get_cards_due()
    
    if not due_card_ids:
        return None, None, None
    
    # Get the first card
    card_id = due_card_ids[0]
    
    # Load the card content
    front_content, back_content = load_card_content(card_id)
    
    # Return the card ID, front, and back content
    return card_id, front_content, back_content

def get_all_cards_due():
    """
    Get all cards that are due for review.
    
    Returns:
        list: A list of dictionaries with card information.
    """
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

def get_card_stats(card_id):
    """
    Get statistics for a card.
    
    Args:
        card_id (str): The ID of the card to get statistics for.
        
    Returns:
        dict: A dictionary with card statistics, or None if the card is not found.
    """
    card = get_card_by_id(card_id)
    
    if not card:
        return None
    
    # Return basic stats
    stats = {
        "due": card.due,
        "state": card.state.name if card.state else "Unknown",
        "reps": card.reps,
        "lapses": card.lapses,
        "stability": round(card.stability, 2) if card.stability else 0,
        "difficulty": round(card.difficulty, 2) if card.difficulty else 0,
    }
    
    # Calculate retrievability if possible
    try:
        stats["retrievability"] = round(card.get_retrievability() * 100, 1)
    except Exception:
        stats["retrievability"] = None
    
    return stats

def get_card_review_history(card_id):
    """
    Get the review history for a card.
    
    Args:
        card_id (str): The ID of the card to get the review history for.
        
    Returns:
        list: A list of dictionaries with review history information.
    """
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
            
            # Map rating number to readable name
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
            # Skip entries with invalid data
            continue
    
    return history

def get_retention_stats():
    """
    Calculate retention statistics for all reviews.
    
    Returns:
        dict: A dictionary with retention statistics.
    """
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    
    # Get total reviews
    c.execute("SELECT COUNT(*) FROM review_log")
    total_reviews = c.fetchone()[0] or 0
    
    # Get total "Again" ratings (1)
    c.execute("SELECT COUNT(*) FROM review_log WHERE rating = '1'")
    again_ratings = c.fetchone()[0] or 0
    
    # Calculate retention rate
    retention_rate = 0
    if total_reviews > 0:
        retention_rate = (total_reviews - again_ratings) / total_reviews
    
    # Get average rating
    c.execute("SELECT AVG(CAST(rating AS REAL)) FROM review_log")
    avg_rating_result = c.fetchone()[0]
    avg_rating = avg_rating_result if avg_rating_result is not None else 0
    
    # Get counts for each rating
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

def get_cards_by_tag(tag):
    """
    Get all cards with a specific tag.
    
    Args:
        tag (str): The tag to search for.
        
    Returns:
        list: A list of card IDs that have the specified tag.
    """
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    
    # Use LIKE with wildcards to find cards that have this tag
    # (assuming tags are stored as comma-separated values)
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

def get_scheduler_with_custom_parameters(desired_retention=0.9):
    """
    Get an FSRS scheduler with custom parameters.
    
    Args:
        desired_retention (float, optional): The desired retention rate (0-1). Defaults to 0.9.
        
    Returns:
        Scheduler: An FSRS Scheduler object with custom parameters.
    """
    # Create a scheduler with the specified desired retention
    return Scheduler(desired_retention=desired_retention)

def reset_card_progress(card_id):
    """
    Reset a card's progress to be a new card.
    
    Args:
        card_id (str): The ID of the card to reset.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    # Create a new card (which resets all progress)
    new_card = Card()
    
    try:
        # Update the card in the database
        update_card(card_id, new_card)
        return True
    except Exception:
        return False

def get_due_count():
    """
    Get the count of cards due for review.
    
    Returns:
        int: The number of cards due for review.
    """
    return len(get_cards_due())

def get_review_interface_data():
    """
    Get data needed for a review interface.
    
    Returns:
        dict: Information needed for a review interface, or None if no cards are due.
    """
    card_id, front_content, back_content = get_next_card_for_review()
    
    if not card_id:
        return None
    
    card = get_card_by_id(card_id)
    
    if not card:
        return None
    
    # Get card stats
    stats = get_card_stats(card_id)
    
    return {
        "id": card_id,
        "front": front_content,
        "back": back_content,
        "stats": stats
    }




