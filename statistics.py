#!/usr/bin/env python3
import curses
import sqlite3
import datetime
from pathlib import Path
import calendar
import math
from collections import defaultdict

# Import from other modules
from config import db_path, colors, ui_colors, symbols
from card_operations import get_retention_stats, get_due_count

def get_review_history_by_day(days_back=365):
    """
    Get the review history grouped by day for the heatmap.
    
    Args:
        days_back (int): Number of days to look back.
        
    Returns:
        dict: A dictionary with dates as keys and review counts as values.
    """
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    
    # Calculate the start date
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days_back)).isoformat()
    
    # Get review counts by day
    c.execute("""
        SELECT substr(review_date, 1, 10) as review_day, COUNT(*) as count
        FROM review_log
        WHERE review_date >= ?
        GROUP BY review_day
        ORDER BY review_day
    """, (start_date,))
    
    results = c.fetchall()
    conn.close()
    
    # Convert to dictionary
    review_counts = {}
    for day, count in results:
        try:
            # Parse the date from ISO format
            date = datetime.date.fromisoformat(day)
            review_counts[date] = count
        except (ValueError, TypeError):
            # Skip invalid dates
            continue
    
    return review_counts

def get_cards_due_next_days(days=7):
    """
    Get the number of cards due for the next X days.
    
    Args:
        days (int): Number of days to look ahead.
        
    Returns:
        dict: A dictionary with dates as keys and due card counts as values.
    """
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    
    due_counts = {}
    now = datetime.datetime.now()
    
    for day in range(days):
        # Calculate the target date
        target_date = now + datetime.timedelta(days=day)
        next_date = now + datetime.timedelta(days=day+1)
        
        # Convert to ISO format for string comparison
        target_iso = target_date.isoformat()
        next_iso = next_date.isoformat()
        
        # Count cards due on this day
        c.execute("""
            SELECT COUNT(*) FROM schedulling
            WHERE due >= ? AND due < ?
        """, (target_iso, next_iso))
        
        count = c.fetchone()[0] or 0
        due_counts[target_date.date()] = count
    
    conn.close()
    return due_counts

def get_cards_due(date=None):
    """
    Get all cards that are due for review on a specific date.
    
    Args:
        date (datetime.date, optional): The date to check. Defaults to today.
        
    Returns:
        list: A list of card IDs that are due for review.
    """
    if date is None:
        date = datetime.datetime.now()
        
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    
    # Convert date to ISO format string
    date_str = date.isoformat()
    next_day = (date + datetime.timedelta(days=1)).isoformat()
    
    c.execute("""
        SELECT command FROM schedulling
        WHERE due >= ? AND due < ?
    """, (date_str, next_day))
    
    cards = c.fetchall()
    conn.close()
    
    return [card[0] for card in cards]

def get_advanced_stats():
    """
    Get a collection of advanced statistics about cards and reviews.
    
    Returns:
        dict: A dictionary with various statistics.
    """
    conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
    c = conn.cursor()
    
    stats = {}
    
    # Total number of cards
    c.execute("SELECT COUNT(*) FROM schedulling")
    stats["total_cards"] = c.fetchone()[0] or 0
    
    # Cards by state
    c.execute("""
        SELECT state, COUNT(*) FROM schedulling
        GROUP BY state
    """)
    state_counts = {row[0]: row[1] for row in c.fetchall()}
    
    # Define state names
    state_names = {
        "0": "New",
        "1": "Learning",
        "2": "Review",
        "3": "Relearning"
    }
    
    stats["cards_by_state"] = {
        state_names.get(state, "Unknown"): count
        for state, count in state_counts.items()
    }
    
    # Average difficulty
    c.execute("SELECT AVG(difficulty) FROM schedulling")
    avg_difficulty = c.fetchone()[0]
    stats["avg_difficulty"] = round(avg_difficulty, 2) if avg_difficulty is not None else 0
    
    # Average stability
    c.execute("SELECT AVG(stability) FROM schedulling")
    avg_stability = c.fetchone()[0]
    stats["avg_stability"] = round(avg_stability, 2) if avg_stability is not None else 0
    
    # Cards added over time
    c.execute("""
        SELECT COUNT(*), MIN(last_review), MAX(last_review) FROM schedulling
        WHERE last_review IS NOT NULL
    """)
    result = c.fetchone()
    
    if result and result[1] and result[2]:
        try:
            first_date = datetime.datetime.fromisoformat(result[1])
            last_date = datetime.datetime.fromisoformat(result[2])
            days_diff = (last_date - first_date).days
            
            if days_diff > 0:
                stats["cards_per_day"] = round(result[0] / days_diff, 1)
            else:
                stats["cards_per_day"] = result[0]
        except (ValueError, TypeError):
            stats["cards_per_day"] = 0
    else:
        stats["cards_per_day"] = 0
    
    # Reviews over time
    c.execute("""
        SELECT COUNT(*), MIN(review_date), MAX(review_date) FROM review_log
    """)
    result = c.fetchone()
    
    if result and result[1] and result[2]:
        try:
            first_date = datetime.datetime.fromisoformat(result[1])
            last_date = datetime.datetime.fromisoformat(result[2])
            days_diff = (last_date - first_date).days
            
            if days_diff > 0:
                stats["reviews_per_day"] = round(result[0] / days_diff, 1)
            else:
                stats["reviews_per_day"] = result[0]
        except (ValueError, TypeError):
            stats["reviews_per_day"] = 0
    else:
        stats["reviews_per_day"] = 0
    
    # Get retention stats
    retention_stats = get_retention_stats()
    stats.update(retention_stats)
    
    conn.close()
    return stats

def draw_heatmap(stdscr, start_y, start_x, width, review_counts, days_back=365):
    """
    Draw a GitHub-like heatmap showing review activity.
    
    Args:
        stdscr: The curses window object.
        start_y (int): The starting Y position.
        start_x (int): The starting X position.
        width (int): The width of the heatmap.
        review_counts (dict): The review counts by day.
        days_back (int): Number of days to display.
    """
    # Get terminal dimensions to ensure we don't try to draw outside the screen
    terminal_height, terminal_width = stdscr.getmaxyx()
    
    # Check if we have enough space to draw the heatmap
    if start_y + 15 > terminal_height or start_x + 10 > terminal_width:
        return False
    
    # Calculate layout parameters
    today = datetime.date.today()
    weeks = math.ceil(days_back / 7)
    
    # Adjust weeks based on available width
    available_width = width - 10  # Subtract for labels
    weeks = min(weeks, available_width // 2)  # Ensure at least 2 chars per week
    
    # If we don't have enough space for even one week, return False
    if weeks <= 0:
        return False
    
    week_width = max(1, math.floor(available_width / weeks) if weeks > 0 else 1)
    
    # Calculate max review count for color scaling
    max_count = max(review_counts.values()) if review_counts else 1
    
    # Draw title
    stdscr.attron(curses.color_pair(ui_colors["title"]))
    stdscr.addstr(start_y, start_x, "Review Activity")
    stdscr.attroff(curses.color_pair(ui_colors["title"]))
    
    # Draw month labels
    month_positions = {}
    for i in range(weeks):
        week_date = today - datetime.timedelta(days=(weeks-i-1)*7)
        month_name = week_date.strftime("%b")
        month_key = week_date.strftime("%Y-%m")
        
        if month_key not in month_positions:
            month_positions[month_key] = start_x + 4 + i * week_width
    
    month_y = start_y + 2
    for month_key, x_pos in month_positions.items():
        year, month = month_key.split("-")
        month_name = datetime.date(int(year), int(month), 1).strftime("%b")
        if month_y < terminal_height and x_pos < terminal_width:
            try:
                stdscr.addstr(month_y, x_pos, month_name, curses.color_pair(ui_colors["info"]))
            except curses.error:
                # Catch errors if we try to draw outside the window
                pass
    
    # Draw day labels
    days = ["Mon", "Wed", "Fri"]
    for i, day in enumerate(days):
        day_y = start_y + 4 + i*2
        if day_y < terminal_height and start_x + 3 < terminal_width:
            try:
                stdscr.addstr(day_y, start_x, day, curses.color_pair(ui_colors["info"]))
            except curses.error:
                # Catch errors if we try to draw outside the window
                pass
    
    # Draw the heatmap cells
    for i in range(weeks):
        for j in range(7):  # 7 days per week
            # Calculate the date for this cell
            days_offset = (weeks - i - 1) * 7 + (6 - j)  # Adjust for Sunday being first day
            cell_date = today - datetime.timedelta(days=days_offset)
            
            # Get the review count for this date
            count = review_counts.get(cell_date, 0)
            
            # Calculate color intensity based on count
            if count == 0:
                color = 0  # Black for empty cells (color 0)
            else:
                # Scale from light to dark green based on review count
                # Use 5 levels: 1-20%, 21-40%, 41-60%, 61-80%, 81-100%
                intensity = min(5, math.ceil(5 * count / max_count))
                
                # Map intensity to color
                color_map = {
                    1: 28,   # Light green
                    2: 34,   # Green
                    3: 40,   # Medium green
                    4: 46,   # Dark green
                    5: 22    # Very dark green
                }
                
                color = color_map[intensity]
            
            # Calculate position
            cell_y = start_y + 4 + j
            cell_x = start_x + 4 + i * week_width
            
            # Draw the cell if it's within bounds
            if cell_y < terminal_height and cell_x < terminal_width:
                try:
                    stdscr.addstr(cell_y, cell_x, "■", curses.color_pair(color))
                except curses.error:
                    # Catch errors if we try to draw outside the window
                    pass
    
    # Draw legend
    legend_y = start_y + 13
    legend_x = start_x
    
    if legend_y < terminal_height and legend_x < terminal_width:
        try:
            stdscr.addstr(legend_y, legend_x, "Less", curses.color_pair(ui_colors["info"]))
        except curses.error:
            pass
    
    for i in range(5):
        color_map = {
            0: 0,     # Black (Empty)
            1: 28,   # Light green
            2: 34,   # Green
            3: 40,   # Medium green
            4: 46,   # Dark green
        }
        
        legend_box_x = legend_x + 6 + i*2
        if legend_y < terminal_height and legend_box_x < terminal_width:
            try:
                stdscr.addstr(legend_y, legend_box_x, "■", curses.color_pair(color_map[i]))
            except curses.error:
                pass
    
    more_text_x = legend_x + 16
    if legend_y < terminal_height and more_text_x < terminal_width:
        try:
            stdscr.addstr(legend_y, more_text_x, "More", curses.color_pair(ui_colors["info"]))
        except curses.error:
            pass
    
    return True

def draw_calendar(stdscr, start_y, start_x, due_counts):
    """
    Draw a calendar showing cards due in the next 7 days.
    
    Args:
        stdscr: The curses window object.
        start_y (int): The starting Y position.
        start_x (int): The starting X position.
        due_counts (dict): Dictionary with dates and due card counts.
        
    Returns:
        bool: True if the calendar was drawn, False if there wasn't enough space
    """
    # Get terminal dimensions
    terminal_height, terminal_width = stdscr.getmaxyx()
    
    # Check if we have enough space to draw the calendar
    # Need at least 11 rows (title + header + 7 days + margin) and 35 columns
    if start_y + 11 > terminal_height or start_x + 35 > terminal_width:
        return False
    
    # Draw title
    try:
        stdscr.attron(curses.color_pair(ui_colors["title"]))
        stdscr.addstr(start_y, start_x, "Cards Due in Next 7 Days")
        stdscr.attroff(curses.color_pair(ui_colors["title"]))
    except curses.error:
        pass
    
    # Draw the calendar
    today = datetime.date.today()
    
    # Draw header
    header_y = start_y + 2
    if header_y < terminal_height:
        try:
            stdscr.addstr(header_y, start_x, "Day", curses.color_pair(ui_colors["info"]))
            if start_x + 10 < terminal_width:
                stdscr.addstr(header_y, start_x + 10, "Date", curses.color_pair(ui_colors["info"]))
            if start_x + 25 < terminal_width:
                stdscr.addstr(header_y, start_x + 25, "Due Cards", curses.color_pair(ui_colors["info"]))
        except curses.error:
            pass
    
    # Draw days
    for i in range(7):
        day_date = today + datetime.timedelta(days=i)
        day_name = day_date.strftime("%a")
        date_str = day_date.strftime("%Y-%m-%d")
        count = due_counts.get(day_date, 0)
        
        # Determine color based on count
        if count == 0:
            count_color = ui_colors["info"]
        elif count < 10:
            count_color = ui_colors["success"]
        elif count < 25:
            count_color = ui_colors["tag"]  # Yellow
        else:
            count_color = ui_colors["warning"]  # Orange
        
        # Highlight today
        if i == 0:
            day_color = ui_colors["highlight"]
        else:
            day_color = ui_colors["menu_item"]
        
        # Draw row if it's within bounds
        row_y = header_y + 2 + i
        if row_y < terminal_height and start_x < terminal_width:
            try:
                stdscr.addstr(row_y, start_x, day_name, curses.color_pair(day_color))
                if start_x + 10 < terminal_width:
                    stdscr.addstr(row_y, start_x + 10, date_str, curses.color_pair(ui_colors["menu_item"]))
                if start_x + 26 < terminal_width:
                    stdscr.addstr(row_y, start_x + 26, str(count), curses.color_pair(count_color))
            except curses.error:
                pass
    
    return True

def draw_statistics(stdscr, start_y, start_x, stats):
    """
    Draw various statistics in a formatted box.
    
    Args:
        stdscr: The curses window object.
        start_y (int): The starting Y position.
        start_x (int): The starting X position.
        stats (dict): Dictionary with all statistics.
        
    Returns:
        bool: True if statistics were drawn, False if there wasn't enough space
    """
    # Get terminal dimensions
    terminal_height, terminal_width = stdscr.getmaxyx()
    
    # Check if we have enough space to draw the statistics section
    # Need at least 12 rows (title + 10 stats + margin) and 40 columns
    if start_y + 12 > terminal_height or start_x + 40 > terminal_width:
        return False
    
    # Draw title
    try:
        stdscr.attron(curses.color_pair(ui_colors["title"]))
        stdscr.addstr(start_y, start_x, "Flashcard Statistics")
        stdscr.attroff(curses.color_pair(ui_colors["title"]))
    except curses.error:
        pass
    
    # Format key statistics
    stats_list = [
        ("Total Cards", str(stats["total_cards"])),
        ("Cards Due Today", str(get_due_count())),
        ("Average Cards Per Day", str(stats.get("cards_per_day", 0))),
        ("Total Reviews", str(stats.get("total_reviews", 0))),
        ("Average Reviews Per Day", str(stats.get("reviews_per_day", 0))),
        ("Retention Rate", f"{stats.get('retention_rate', 0)}%"),
        ("Average Rating", str(stats.get("avg_rating", 0))),
        ("Average Card Difficulty", str(stats.get("avg_difficulty", 0))),
        ("Average Card Stability", str(stats.get("avg_stability", 0)))
    ]
    
    # Add review distribution
    if "rating_counts" in stats:
        reviews_total = sum(stats["rating_counts"].values())
        
        if reviews_total > 0:
            rating_stats = [
                ("Again Ratings", f"{stats['rating_counts']['Again']} ({stats['rating_counts']['Again']/reviews_total*100:.1f}%)"),
                ("Hard Ratings", f"{stats['rating_counts']['Hard']} ({stats['rating_counts']['Hard']/reviews_total*100:.1f}%)"),
                ("Good Ratings", f"{stats['rating_counts']['Good']} ({stats['rating_counts']['Good']/reviews_total*100:.1f}%)"),
                ("Easy Ratings", f"{stats['rating_counts']['Easy']} ({stats['rating_counts']['Easy']/reviews_total*100:.1f}%)")
            ]
            stats_list.extend(rating_stats)
    
    # Add card state distribution
    if "cards_by_state" in stats:
        cards_total = stats["total_cards"]
        
        if cards_total > 0:
            for state, count in stats["cards_by_state"].items():
                percentage = count / cards_total * 100 if cards_total > 0 else 0
                state_stat = (f"{state} Cards", f"{count} ({percentage:.1f}%)")
                stats_list.append(state_stat)
    
    # Calculate how many stats we can display based on available space
    max_visible_stats = min(terminal_height - start_y - 2, len(stats_list))
    
    # Draw the statistics
    for i, (label, value) in enumerate(stats_list[:max_visible_stats]):
        row_y = start_y + 2 + i
        
        if row_y < terminal_height and start_x < terminal_width:
            try:
                # Draw label
                stdscr.addstr(row_y, start_x, label + ":", curses.color_pair(ui_colors["info"]))
                
                # Draw value if there's enough space
                if start_x + 25 < terminal_width:
                    stdscr.addstr(row_y, start_x + 25, value, curses.color_pair(ui_colors["menu_item"]))
            except curses.error:
                # Skip if out of bounds
                continue
    
    return True

def main():
    """
    Main entry point when the script is run directly.
    This is kept for standalone usage, but the main functionality
    is now integrated into the main menu.
    """
    try:
        curses.wrapper(display_stats_standalone)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        pass
    except Exception as e:
        # Print any errors
        print(f"Error: {e}")

def display_stats_standalone(stdscr):
    """
    Standalone display function for when statistics.py is run directly.
    """
    # Check terminal capabilities
    if not curses.has_colors():
        stdscr.addstr(0, 0, "Error: Your terminal does not support colors.")
        stdscr.refresh()
        stdscr.getch()
        return
        
    # Initialize curses colors
    curses.start_color()
    curses.use_default_colors()
    
    # Initialize color pairs based on the theme
    # Handle terminals with limited color support
    max_colors = min(256, curses.COLORS)
    for i in range(max_colors):
        curses.init_pair(i, i, -1)
    
    # Get terminal dimensions
    height, width = stdscr.getmaxyx()
    
    # Clear screen
    stdscr.clear()
    
    # Draw border
    stdscr.attron(curses.color_pair(ui_colors["border"]))
    stdscr.box()
    stdscr.attroff(curses.color_pair(ui_colors["border"]))
    
    # Draw title
    title = "Excalibur Flashcard Statistics"
    try:
        stdscr.attron(curses.color_pair(ui_colors["title"]))
        stdscr.addstr(1, max(0, (width - len(title)) // 2), title)
        stdscr.attroff(curses.color_pair(ui_colors["title"]))
    except curses.error:
        pass
    
    # Get data for displays
    review_counts = get_review_history_by_day()
    due_counts = get_cards_due_next_days()
    stats = get_advanced_stats()
    
    # Draw components based on available space
    heatmap_drawn = draw_heatmap(stdscr, 3, 2, width - 4, review_counts)
    
    # Draw calendar and statistics if heatmap was drawn and there's space
    if heatmap_drawn:
        heatmap_height = 15  # Approximate height of heatmap
        calendar_start_y = 3 + heatmap_height
        calendar_drawn = draw_calendar(stdscr, calendar_start_y, 2, due_counts)
        
        # If there's enough width, draw statistics next to calendar
        if width >= 80:
            stats_start_x = width // 2
            draw_statistics(stdscr, calendar_start_y, stats_start_x, stats)
        # Otherwise, draw statistics below calendar if there's enough height
        elif calendar_drawn and height >= calendar_start_y + 24:
            stats_start_y = calendar_start_y + 11
            draw_statistics(stdscr, stats_start_y, 2, stats)
    
    # Add instructions at the bottom
    instructions = "Press 'q' to quit, any other key to refresh"
    try:
        stdscr.addstr(height - 2, max(0, (width - len(instructions)) // 2), instructions, 
                      curses.color_pair(ui_colors["info"]))
    except curses.error:
        pass
    
    # Refresh the screen
    stdscr.refresh()
    
    # Wait for user input
    while True:
        key = stdscr.getch()
        
        if key == ord('q'):
            break
        else:
            # Refresh data and redraw
            stdscr.clear()
            stdscr.box()
            
            try:
                stdscr.addstr(1, max(0, (width - len(title)) // 2), title, 
                              curses.color_pair(ui_colors["title"]))
            except curses.error:
                pass
            
            review_counts = get_review_history_by_day()
            due_counts = get_cards_due_next_days()
            stats = get_advanced_stats()
            
            # Draw components based on available space
            heatmap_drawn = draw_heatmap(stdscr, 3, 2, width - 4, review_counts)
            
            if heatmap_drawn:
                heatmap_height = 15
                calendar_start_y = 3 + heatmap_height
                calendar_drawn = draw_calendar(stdscr, calendar_start_y, 2, due_counts)
                
                if width >= 80:
                    stats_start_x = width // 2
                    draw_statistics(stdscr, calendar_start_y, stats_start_x, stats)
                elif calendar_drawn and height >= calendar_start_y + 24:
                    stats_start_y = calendar_start_y + 11
                    draw_statistics(stdscr, stats_start_y, 2, stats)
            
            try:
                stdscr.addstr(height - 2, max(0, (width - len(instructions)) // 2), instructions, 
                              curses.color_pair(ui_colors["info"]))
            except curses.error:
                pass
            
            stdscr.refresh()

if __name__ == "__main__":
    main()
