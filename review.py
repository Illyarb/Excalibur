import curses
import os
import copy
import datetime
from datetime import timedelta
from pathlib import Path
import sys
import tty
import termios

# Import from our modules
from config import db_path, colors, ui_colors
from card_operations import (
    get_next_card_for_review,
    load_card_content,
    review_card,
    get_all_cards_due,
    get_card_stats,
    get_card_by_id
)

# Replace Rich with custom renderer
from renderer import render_markdown

from fsrs import Scheduler, Card, Rating


def format_time_diff(time_diff):
    """Format a time difference in a user-friendly way."""
    minutes = time_diff.total_seconds() / 60
    hours = minutes / 60
    days = hours / 24
    weeks = days / 7
    
    if minutes < 60:
        return f"{int(minutes)}min"
    elif hours < 24:
        return f"{int(hours)}h"
    elif days < 7:
        return f"{int(days)}d"
    else:
        return f"{int(weeks)}w"


def calculate_next_review_dates(card_id: str) -> dict:
    """Calculate the next review dates for each of the possible ratings."""
    scheduler = Scheduler()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Get the card from the database
    card = get_card_by_id(card_id)
    if not card:
        return {1: "N/A", 2: "N/A", 3: "N/A", 4: "N/A"}
    
    next_dates = {}
    for rating_value in range(1, 5):
        rating = Rating(rating_value)
        # Create a copy of the card to avoid modifying the original
        card_copy = copy.deepcopy(card)
        # Simulate a review with this rating
        updated_card, _ = scheduler.review_card(card_copy, rating)
        # Calculate the time difference
        if updated_card.due:
            time_diff = updated_card.due - now
            next_dates[rating_value] = format_time_diff(time_diff)
        else:
            next_dates[rating_value] = "N/A"
    
    return next_dates


class ReviewUI:
    def __init__(self, stdscr, status_bar):
        self.stdscr = stdscr
        self.status_bar = status_bar
        self.height, self.width = stdscr.getmaxyx()
    
    def get_keypress(self):
        """Get a keypress when curses is not active."""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            
            # Handle arrow keys which send escape sequences
            if ch == '\x1b':
                ch += sys.stdin.read(2)
                
                # Map escape sequences to arrow key names
                if ch == '\x1b[A':
                    return 'KEY_UP'
                elif ch == '\x1b[B':
                    return 'KEY_DOWN'
                elif ch == '\x1b[C':
                    return 'KEY_RIGHT'
                elif ch == '\x1b[D':
                    return 'KEY_LEFT'
            
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def print_colored_status_at_bottom(self, next_review_dates):
        """Print a colored status bar with next review dates."""
        terminal_width, terminal_height = os.get_terminal_size()
        
        # Format strings for each rating
        again_str = f"Again(l) - {next_review_dates[1]}"
        hard_str = f"Hard(k) - {next_review_dates[2]}"
        good_str = f"Good(j) - {next_review_dates[3]}"
        easy_str = f"Easy(h) - {next_review_dates[4]}"
        
        # Full status text with separators
        status_text = f"{again_str} | {hard_str} | {good_str} | {easy_str}"
        
        # Center the status text
        padding = (terminal_width - len(status_text)) // 2
        
        # Move cursor to the last line and clear it
        print(f"\033[{terminal_height};0H", end="")
        print(" " * terminal_width, end="")
        print(f"\033[{terminal_height};0H", end="")
        
        # Print centered text with different colors
        print(" " * padding, end="")
        
        # Print each section with appropriate color
        # Again - Red
        print(f"\033[31m{again_str}\033[0m", end="")
        print(" | ", end="")
        
        # Hard - Orange/Yellow
        print(f"\033[33m{hard_str}\033[0m", end="")
        print(" | ", end="")
        
        # Good - Green
        print(f"\033[32m{good_str}\033[0m", end="")
        print(" | ", end="")
        
        # Easy - Cyan
        print(f"\033[36m{easy_str}\033[0m", end="")
        
        # Move cursor back to top left
        print(f"\033[1;1H", end="")
    
    def draw_review_stats(self, card_id):
        """Display statistics about a card during review."""
        # Get card stats
        stats = get_card_stats(card_id)
        
        if not stats:
            return
        
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Create box for stats
        box_height = 12
        box_width = 50
        start_y = (height - box_height) // 2
        start_x = (width - box_width) // 2
        
        # Draw border
        self.draw_border(start_y, start_x, box_height, box_width, "Card Statistics")
        
        # Display stats
        content_x = start_x + 4
        content_y = start_y + 3
        
        # Format due date
        due_str = "N/A"
        if stats["due"]:
            due_str = stats["due"].strftime("%Y-%m-%d %H:%M")
        
        # Display stats with different colors
        self.stdscr.addstr(content_y, content_x, "State: ", curses.color_pair(3))
        self.stdscr.addstr(content_y, content_x + 7, stats["state"], curses.color_pair(2))
        
        self.stdscr.addstr(content_y + 1, content_x, "Due: ", curses.color_pair(3))
        self.stdscr.addstr(content_y + 1, content_x + 5, due_str, curses.color_pair(2))
        
        self.stdscr.addstr(content_y + 2, content_x, "Reviews: ", curses.color_pair(3))
        self.stdscr.addstr(content_y + 2, content_x + 9, str(stats["reps"]), curses.color_pair(2))
        
        self.stdscr.addstr(content_y + 3, content_x, "Lapses: ", curses.color_pair(3))
        self.stdscr.addstr(content_y + 3, content_x + 8, str(stats["lapses"]), curses.color_pair(2))
        
        self.stdscr.addstr(content_y + 4, content_x, "Stability: ", curses.color_pair(3))
        self.stdscr.addstr(content_y + 4, content_x + 11, str(stats["stability"]), curses.color_pair(2))
        
        self.stdscr.addstr(content_y + 5, content_x, "Difficulty: ", curses.color_pair(3))
        self.stdscr.addstr(content_y + 5, content_x + 12, str(stats["difficulty"]), curses.color_pair(2))
        
        # Display retrievability if available
        if stats["retrievability"] is not None:
            self.stdscr.addstr(content_y + 6, content_x, "Retrievability: ", curses.color_pair(3))
            
            # Color based on retrievability value
            retrievability_str = f"{stats['retrievability']}%"
            if stats["retrievability"] >= 90:
                attr = curses.color_pair(7)  # Success/green
            elif stats["retrievability"] >= 70:
                attr = curses.color_pair(9)  # Yellow
            else:
                attr = curses.color_pair(6)  # Error/red
            
            self.stdscr.addstr(content_y + 6, content_x + 15, retrievability_str, attr)
        
        # Instructions to return
        self.stdscr.addstr(content_y + 8, content_x, "Press any key to continue...", curses.color_pair(8))
        self.stdscr.refresh()
        self.stdscr.getch()
    
    def draw_border(self, y, x, height, width, title=""):
        # Top border with title
        self.stdscr.addstr(y, x, "╭" + "─" * (width - 2) + "╮", curses.color_pair(3))
        if title:
            title = f" {title} "
            title_pos = x + (width - len(title)) // 2
            self.stdscr.addstr(y, title_pos, title, curses.color_pair(1) | curses.A_BOLD)
        
        # Side borders
        for i in range(1, height - 1):
            self.stdscr.addstr(y + i, x, "│", curses.color_pair(3))
            self.stdscr.addstr(y + i, x + width - 1, "│", curses.color_pair(3))
        
        # Bottom border
        self.stdscr.addstr(y + height - 1, x, "╰" + "─" * (width - 2) + "╯", curses.color_pair(3))
    
    def run(self):
        """Display the review interface using the custom markdown renderer."""
        # Get all due cards
        due_cards = get_all_cards_due()

        if not due_cards:
            # Display message using status bar
            self.status_bar.clear()
            message = "No cards due for review!"
            message_x = max(0, (self.width - len(message)) // 2)
            self.status_bar.addstr(0, message_x, message, curses.color_pair(8))
            self.status_bar.refresh()
            curses.napms(1500)  # Display for 1.5 seconds
            self.status_bar.clear()
            self.status_bar.refresh()
            return

        # Initialize review session state
        current_card_idx = 0
        show_answer = False
        exit_review = False

        # Save current terminal state
        curses.def_prog_mode()
        curses.endwin()

        while not exit_review and current_card_idx < len(due_cards):
            # Get current card
            card = due_cards[current_card_idx]
            card_id = card["id"]
            front_content = card["front"]
            back_content = card["back"]
            
            # Calculate next review dates for different ratings
            next_review_dates = calculate_next_review_dates(card_id)
            
            # Clear screen
            os.system('clear' if os.name == 'posix' else 'cls')
            
            # Get terminal dimensions
            terminal_width, terminal_height = os.get_terminal_size()
            
            # Print status bar at the bottom with next review dates if showing answer
            if show_answer:
                self.print_colored_status_at_bottom(next_review_dates)
            else:
                # Move cursor to last line and clear it if not showing answer
                print(f"\033[{terminal_height};0H", end="")
                print(" " * terminal_width, end="")
                print(f"\033[1;1H", end="")
            
            # Display content using the custom renderer
            content = front_content if not show_answer else back_content
            
            # Use custom markdown renderer instead of Rich
            rendered_content = render_markdown(content)
            print(rendered_content)
            
            # Get user input
            try:
                key = self.get_keypress()
                
                if not show_answer and key in ('h', ' ', 'KEY_RIGHT'):
                    # Show answer 
                    show_answer = True
                elif show_answer and key == ' ':
                    # Toggle back to front if space is pressed while showing answer
                    show_answer = False
                elif show_answer and key in ('l', 'k', 'j', 'h'):
                    # Rate card if showing answer
                    rating_map = {
                        'l': 1,  # Again
                        'k': 2,  # Hard
                        'j': 3,  # Good
                        'h': 4,  # Easy
                    }
                    
                    # Review the card with the selected rating
                    review_card(card_id, rating_map[key])
                    
                    # Move to the next card
                    current_card_idx += 1
                    show_answer = False
                elif key == 'q':
                    exit_review = True
            except Exception as e:
                print(f"\033[31mError: {e}\033[0m")
                import time
                time.sleep(2)

        # If we've gone through all cards
        if current_card_idx >= len(due_cards) and not exit_review:
            os.system('clear' if os.name == 'posix' else 'cls')
            
            # Get terminal dimensions
            terminal_width, terminal_height = os.get_terminal_size()
            
            # Calculate vertical centering for completion message
            padding_lines = terminal_height // 3
            
            # Print top padding
            for _ in range(padding_lines):
                print("")
                
            # Create a simple centered completion message
            completion_message = "Congratulations! You've completed all due cards!"
            padding = (terminal_width - len(completion_message)) // 2
            print(" " * padding + "\033[1;32m" + completion_message + "\033[0m")
            
            # Wait for a keypress before returning
            self.get_keypress()

        # Restore terminal state for curses
        curses.reset_prog_mode()
        self.stdscr.refresh()
