import curses
import os
import copy
import datetime
import sys
import tty
import termios
from datetime import timedelta
from pathlib import Path
from typing import Dict

# Rich imports for markdown rendering
from rich.console import Console
from rich.markdown import Markdown
from rich.align import Align
from rich.text import Text
from rich.panel import Panel

# Import from our modules
from base_ui import BaseUI
from config import db_path, colors
from card_operations import (
    get_next_card_for_review, 
    load_card_content,
    review_card,
    get_all_cards_due,
    get_card_stats,
    get_card_by_id
)
from fsrs import Scheduler, Card, Rating


class ReviewMenu(BaseUI):
    def __init__(self, stdscr):
        super().__init__(stdscr)
    
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
    
    def format_time_diff(self, time_diff):
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
    
    def calculate_next_review_dates(self, card_id: str) -> Dict[int, str]:
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
                next_dates[rating_value] = self.format_time_diff(time_diff)
            else:
                next_dates[rating_value] = "N/A"
        
        return next_dates
    
    def print_colored_status_at_bottom(self, next_review_dates):
        """Print a colored status bar with next review dates."""
        terminal_width, terminal_height = os.get_terminal_size()
        
        # Format strings for each rating
        again_str = f"Again(l) - {next_review_dates[1]}"
        hard_str = f"Hard(k) - {next_review_dates[2]}"
        good_str = f"Good(j) - {next_review_dates[3]}"
        easy_str = f"Easy(h) - {next_review_dates[4]}"
        
        # Full status text with separators
        status_text = f"{easy_str} | {good_str} | {hard_str} | {again_str}"

        
        # Center the status text
        padding = (terminal_width - len(status_text)) // 2
        
        # Move cursor to the last line and clear it
        print(f"\033[{terminal_height};0H", end="")
        print(" " * terminal_width, end="")
        print(f"\033[{terminal_height};0H", end="")
        
        # Print centered text with different colors
        print(" " * padding, end="")
        
        # Print each section with appropriate color
        
        
        
        # Easy - Cyan
        print(f"\033[36m{easy_str}\033[0m", end="")
        print(" | ", end="")

        # Good - Green
        print(f"\033[32m{good_str}\033[0m", end="")
        print(" | ", end="")

        # Hard - Orange/Yellow
        print(f"\033[33m{hard_str}\033[0m", end="")
        print(" | ", end="")

        # Again - Red
        print(f"\033[31m{again_str}\033[0m", end="")

        
        # Move cursor back to top left
        print(f"\033[1;1H", end="")

    def show_edit_menu(self, card_id, front_content, back_content):
        """Display a menu for editing the current card."""
        # Save current terminal state
        curses.def_prog_mode()
        curses.endwin()
        
        # Clear the screen
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # Get terminal dimensions
        terminal_width, terminal_height = os.get_terminal_size()
        
        # Print the edit menu
        console = Console()
        
        # Add some vertical padding
        padding_lines = terminal_height // 6
        for _ in range(padding_lines):
            console.print("")
        
        # Print title
        title = Text("Card Edit Menu", style="bold cyan")
        console.print(Align.center(title))
        console.print("")
        
        # Print options
        options = [
            ("f", "Edit front of card", "yellow"),
            ("b", "Edit back of card", "yellow"),
            ("p", "Edit card parameters", "yellow"),
            ("d", "Delete card", "red"),
            ("c", "Cancel and return to review", "green")
        ]
        
        for key, description, color in options:
            option_text = Text(f"{key} - {description}", style=color)
            console.print(Align.center(option_text))
        
        console.print("")
        prompt = Text("Press a key to select an option:", style="bold")
        console.print(Align.center(prompt))
        
        # Get user input
        while True:
            key = self.get_keypress()
            
            if key == 'f':
                # Edit front content
                self.edit_card_content(card_id, "front", front_content)
                break
            elif key == 'b':
                # Edit back content
                self.edit_card_content(card_id, "back", back_content)
                break
            elif key == 'p':
                # Edit parameters
                self.edit_card_parameters(card_id)
                break
            elif key == 'd':
                # Delete card
                if self.confirm_delete_card(card_id):
                    # Restore terminal state
                    curses.reset_prog_mode()
                    self.stdscr.refresh()
                    return True  # Return True to indicate card was deleted
                else:
                    break
            elif key == 'c' or key == 'q':
                # Cancel
                break
        
        # Restore terminal state
        curses.reset_prog_mode()
        self.stdscr.refresh()
        return False  # Card was not deleted

    def edit_card_content(self, card_id, side, current_content):
        """Edit the content of a card (front or back)."""
        from pathlib import Path
        from config import db_path, editor
        
        # Prepare file path
        file_path = Path(db_path + f"/cards/{card_id}_{side}.md").expanduser()
        
        # Save current content to a temporary file if it doesn't exist
        if not file_path.exists():
            with open(file_path, 'w') as f:
                f.write(current_content)
        
        # Open the editor with the file
        try:
            subprocess.run([editor, str(file_path)])
        except Exception as e:
            # If there's an error with the configured editor, fall back to a simple one
            fallback_editors = ['nano', 'vim', 'vi', 'notepad']
            for fallback in fallback_editors:
                try:
                    subprocess.run([fallback, str(file_path)])
                    break
                except Exception:
                    continue
        
        # The file is saved by the editor, so we're done
        return

    def edit_card_parameters(self, card_id):
        """Edit scheduling parameters of a card."""
        from card_operations import get_card_by_id, update_card
        from fsrs import State
        
        # Get current parameters
        card = get_card_by_id(card_id)
        if not card:
            return
        
        # Save current terminal state
        curses.def_prog_mode()
        curses.endwin()
        
        # Clear the screen
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # Get terminal dimensions
        terminal_width, terminal_height = os.get_terminal_size()
        
        # Display a form-like interface for editing parameters
        console = Console()
        
        # Add some vertical padding
        padding_lines = terminal_height // 8
        for _ in range(padding_lines):
            console.print("")
        
        # Print title
        title = Text("Edit Card Parameters", style="bold cyan")
        console.print(Align.center(title))
        console.print("")
        
        # Print current values
        console.print(Align.center(Text(f"Current Difficulty: {card.difficulty:.2f}", style="yellow")))
        console.print(Align.center(Text(f"Current Stability: {card.stability:.2f}", style="yellow")))
        current_state = card.state.name if card.state else "NEW"
        console.print(Align.center(Text(f"Current State: {current_state}", style="yellow")))
        due_date = card.due.strftime("%Y-%m-%d %H:%M") if card.due else "Not set"
        console.print(Align.center(Text(f"Current Due Date: {due_date}", style="yellow")))
        console.print("")
        
        # Instructions
        console.print(Align.center(Text("Enter new values (leave blank to keep current value)", style="cyan")))
        console.print("")
        
        # Function to get input with prompt
        def get_input(prompt, default=""):
            console.print(Align.center(Text(prompt, style="bold")))
            # Move to center of screen for input
            padding = (terminal_width - 30) // 2
            print(" " * padding, end="")
            return input() or default
        
        # Get user input for each parameter
        try:
            # Get difficulty
            new_difficulty = get_input(f"New Difficulty (0.0-10.0) [{card.difficulty:.2f}]: ", str(card.difficulty))
            try:
                card.difficulty = float(new_difficulty)
                # Keep within valid range
                card.difficulty = max(0.0, min(10.0, card.difficulty))
            except ValueError:
                pass
            
            # Get stability
            new_stability = get_input(f"New Stability (>= 0.0) [{card.stability:.2f}]: ", str(card.stability))
            try:
                card.stability = float(new_stability)
                # Keep within valid range
                card.stability = max(0.0, card.stability)
            except ValueError:
                pass
            
            # Get state (show options)
            console.print(Align.center(Text("States: 0=NEW, 1=LEARNING, 2=REVIEW, 3=RELEARNING", style="cyan")))
            new_state = get_input(f"New State (0-3) [{card.state.value if card.state else 0}]: ", 
                                 str(card.state.value if card.state else 0))
            try:
                state_value = int(new_state)
                if 0 <= state_value <= 3:
                    card.state = State(state_value)
            except (ValueError, TypeError):
                pass
            
            # Get due date (format: YYYY-MM-DD HH:MM)
            console.print(Align.center(Text("Format: YYYY-MM-DD HH:MM (e.g., 2023-12-31 14:30)", style="cyan")))
            new_due_date = get_input(f"New Due Date [{due_date}]: ", due_date)
            if new_due_date != due_date:
                try:
                    card.due = datetime.datetime.strptime(new_due_date, "%Y-%m-%d %H:%M")
                    # Add UTC timezone
                    card.due = card.due.replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    console.print(Align.center(Text("Invalid date format. Keeping current value.", style="red")))
                    # Wait for user acknowledgment
                    console.print(Align.center(Text("Press any key to continue...", style="bold")))
                    self.get_keypress()
            
            # Update the card
            update_card(card_id, card)
            
            console.print("")
            console.print(Align.center(Text("Parameters updated successfully!", style="green bold")))
            
        except Exception as e:
            console.print(Align.center(Text(f"Error: {str(e)}", style="red bold")))
        
        # Wait for user to acknowledge
        console.print("")
        console.print(Align.center(Text("Press any key to return...", style="bold")))
        self.get_keypress()
        
        # Restore terminal state
        curses.reset_prog_mode()
        self.stdscr.refresh()

    def confirm_delete_card(self, card_id):
        """Confirm and delete a card."""
        from card_operations import delete_card
        
        # Save current terminal state
        curses.def_prog_mode()
        curses.endwin()
        
        # Clear the screen
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # Get terminal dimensions
        terminal_width, terminal_height = os.get_terminal_size()
        
        # Print confirmation prompt
        console = Console()
        
        # Add some vertical padding
        padding_lines = terminal_height // 3
        for _ in range(padding_lines):
            console.print("")
        
        # Print warning
        warning = Text("⚠️  WARNING: You are about to delete this card  ⚠️", style="bold red")
        console.print(Align.center(warning))
        console.print("")
        
        prompt = Text("Are you sure? This action cannot be undone. (y/n)", style="yellow")
        console.print(Align.center(prompt))
        
        # Get user input
        while True:
            key = self.get_keypress()
            
            if key.lower() == 'y':
                # Delete the card
                success = delete_card(card_id)
                
                # Show result
                if success:
                    console.print("")
                    console.print(Align.center(Text("Card deleted successfully.", style="green")))
                else:
                    console.print("")
                    console.print(Align.center(Text("Failed to delete card!", style="red")))
                
                # Wait for a keypress
                console.print("")
                console.print(Align.center(Text("Press any key to continue...", style="bold")))
                self.get_keypress()
                
                return success
            elif key.lower() == 'n' or key == '\x1b':  # 'n' or Escape
                return False
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
    
    def run(self):
        """Display the review interface for reviewing cards with centered markdown using Rich."""
        # Get all due cards
        due_cards = get_all_cards_due()

        if not due_cards:
            self.draw_message("No cards due for review!", "info")
            return

        # Initialize review session state
        current_card_idx = 0
        show_answer = False
        exit_review = False

        # Save current terminal state
        curses.def_prog_mode()
        curses.endwin()

        # Initialize Rich console
        console = Console()

        while not exit_review and current_card_idx < len(due_cards):
            # Get current card
            card = due_cards[current_card_idx]
            card_id = card["id"]
            front_content = card["front"]
            back_content = card["back"]
            
            # Calculate next review dates for different ratings
            next_review_dates = self.calculate_next_review_dates(card_id)
            
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
            
            # Calculate vertical centering for the card content
            content_lines = (front_content if not show_answer else back_content).count('\n') + 6  # Add buffer for markdown rendering
            
            # Calculate padding for vertical centering (leave room for status bar)
            padding_lines = max(0, (terminal_height - content_lines - 1) // 2 - 2)
            
            # Print top padding
            for _ in range(padding_lines):
                console.print("")
            
            # Display content with proper centering
            if not show_answer:
                # Display front of card
                md = Markdown(front_content, justify="center")
                panel = Panel(md, border_style="none", expand=False, padding=(0, 2))
                console.print(Align.center(panel))
                
                # Instructions for revealing answer
                show_answer_hint = "Press Space to show answer, 'q' to quit, 'e' to edit"
                # print(f"\033[{terminal_height-2};0H", end="")
                # print(" " * ((terminal_width - len(show_answer_hint)) // 2) + show_answer_hint, end="")
                # print(f"\033[1;1H", end="")
            else:
                # Display back of card
                md = Markdown(back_content, justify="center")
                panel = Panel(md, border_style="none", expand=False, padding=(0, 2))
                console.print(Align.center(panel))
                
                # Instructions for rating or editing (in addition to the colored status bar)
                rating_hint = "Rate card: l:Again k:Hard j:Good h:Easy | 'e' to Edit | Space to toggle, 'q' to quit"
                # print(f"\033[{terminal_height-2};0H", end="")
                # print(" " * ((terminal_width - len(rating_hint)) // 2) + rating_hint, end="")
                # print(f"\033[1;1H", end="")
            
            # Get user input
            try:
                key = self.get_keypress()
                
                if key == 'e':
                    # Show edit menu
                    card_deleted = self.show_edit_menu(card_id, front_content, back_content)
                    
                    if card_deleted:
                        # Remove the card from the due_cards list
                        due_cards.pop(current_card_idx)
                        
                        if not due_cards:
                            # If no more cards, exit review
                            exit_review = True
                        continue  # Skip the rest of the loop to refresh the display
                    
                    # Reload card content in case it was edited
                    updated_front, updated_back = load_card_content(card_id)
                    if updated_front:
                        due_cards[current_card_idx]["front"] = updated_front
                        front_content = updated_front
                    if updated_back:
                        due_cards[current_card_idx]["back"] = updated_back
                        back_content = updated_back
                    
                    # Continue showing the same side
                    continue  # Skip the rest of the loop to refresh the display
                elif not show_answer and key in ('h', ' ', 'KEY_RIGHT'):
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
                console.print(f"Error: {e}")
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
                console.print("")
                
            # Create a simple centered completion message
            completion_message = Text("Congratulations! You've completed all due cards!", style="bold green")
            console.print(Align.center(completion_message))
            
            # Wait for a keypress before returning
            self.get_keypress()

        # Restore terminal state for curses
        curses.reset_prog_mode()
        self.stdscr.refresh()

def main(stdscr):
    """Initialize and run the review menu directly (for testing)"""
    ui = ReviewMenu(stdscr)
    ui.run()


if __name__ == "__main__":
    curses.wrapper(main)
