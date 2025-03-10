import curses
from curses import wrapper
from typing import List, Set, Dict
from db_operations import new_tag, get_tags, add_card, get_cards_due
import subprocess
import os
from pathlib import Path
from config import db_path, editor, ui_colors, symbols, colors
import uuid
import copy
import datetime
from datetime import timedelta
# Use Rich for rendering, with special handling for centering
from rich.console import Console
from rich.markdown import Markdown
from rich.align import Align
from rich.text import Text
from rich.panel import Panel
from fsrs import Scheduler, Card, State, Rating, ReviewLog
from card_operations import (
    get_next_card_for_review, 
    load_card_content,
    review_card,
    get_all_cards_due,
    get_card_stats,
    get_card_by_id
)

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

def calculate_next_review_dates(card_id: str) -> Dict[int, str]:
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

class FlashcardUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.tags = get_tags()
        self.selected_tags: Set[str] = set()
        self.due_cards = get_cards_due()
        
        # Setup curses
        curses.curs_set(0)  # Disable cursor
        curses.use_default_colors()
        self.init_colors()
        self.current_idx = 0
        
        # Create status bar window
        self.height, self.width = stdscr.getmaxyx()
        self.status_bar = curses.newwin(1, self.width, self.height-1, 0)
        self.status_bar.bkgd(' ', curses.color_pair(11))  # Status bar background
    
    def init_colors(self):
        """Initialize color pairs for the UI"""
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs based on ui_colors
        curses.init_pair(1, ui_colors["title"], -1)  # Title
        curses.init_pair(2, ui_colors["menu_item"], -1)  # Menu item
        curses.init_pair(3, ui_colors["selected_item"], -1)  # Selected item
        curses.init_pair(4, ui_colors["highlight"], -1)  # Highlight
        curses.init_pair(5, ui_colors["warning"], -1)  # Warning
        curses.init_pair(6, ui_colors["error"], -1)  # Error
        curses.init_pair(7, ui_colors["success"], -1)  # Success
        curses.init_pair(8, ui_colors["info"], -1)  # Info
        curses.init_pair(9, ui_colors["tag"], -1)  # Tag
        curses.init_pair(10, ui_colors["selected_tag"], -1)  # Selected tag
        curses.init_pair(11, ui_colors["status_text"], ui_colors["status_bar"])  # Status bar
        
        # Special status line colors for ratings
        curses.init_pair(12, colors["red"], ui_colors["status_bar"])     # Again (red)
        curses.init_pair(13, colors["orange"], ui_colors["status_bar"])  # Hard (orange)
        curses.init_pair(14, colors["green"], ui_colors["status_bar"])   # Good (green)
        curses.init_pair(15, colors["cyan"], ui_colors["status_bar"])    # Easy (cyan)

    def draw_message(self, message: str, message_type="info"):
        """Draw a message in the status bar"""
        self.status_bar.clear()
        color_map = {
            "info": 8,      # Info color
            "warning": 5,   # Warning color
            "error": 6,     # Error color
            "success": 7,   # Success color
        }
        color_pair = color_map.get(message_type, 8)
        
        # Center the message
        message_x = max(0, (self.width - len(message)) // 2)
        self.status_bar.addstr(0, message_x, message, curses.color_pair(color_pair))
        self.status_bar.refresh()
        curses.napms(1500)  # Display for 1.5 seconds
        self.status_bar.clear()
        self.status_bar.refresh()

    def create_card(self):
        """Create a new flashcard with selected tags"""
        card_id = str(uuid.uuid4())
        scripts_dir = Path(db_path + "/cards").expanduser()
        
        
        # Save current terminal state
        curses.def_prog_mode()
        curses.endwin()
        
        # Create front of card
        front_path = scripts_dir / f"{card_id}_front.md"
        subprocess.run([editor, str(front_path)])
        
        # Restore terminal state
        curses.reset_prog_mode()
        self.stdscr.refresh()
        
        
        # Save current terminal state again
        curses.def_prog_mode()
        curses.endwin()
        
        # Create back of card
        back_path = scripts_dir / f"{card_id}_back.md"
        subprocess.run([editor, str(back_path)])
        
        # Restore terminal state
        curses.reset_prog_mode()
        self.stdscr.refresh()
        
        if front_path.exists() and back_path.exists():
            add_card(card_id, ",".join(self.selected_tags))
            self.draw_message(f"Card created successfully", "success")
        else:
            self.draw_message("Failed to create card", "error")

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

    def draw_manage_tags(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Calculate box dimensions
        box_height = min(len(self.tags) + 6, height - 4)
        box_width = 40
        start_y = (height - box_height) // 2
        start_x = (width - box_width) // 2
        
        # Draw border
        self.draw_border(start_y, start_x, box_height, box_width, "Manage Tags")
        
        # Draw instructions - removed vim keybindings
        instructions = " Move: ↑/↓   Add: a   Select: Space   Back: q "
        instr_pos = start_x + (box_width - len(instructions)) // 2
        self.stdscr.addstr(start_y + 2, instr_pos, instructions, curses.color_pair(8))
        
        # Draw horizontal separator
        self.stdscr.addstr(start_y + 3, start_x + 1, "─" * (box_width - 2), curses.color_pair(3))
        
        self.current_idx = 0
        
        tag_start_y = start_y + 4
        content_x = start_x + 2
        max_visible_tags = box_height - 6
        
        while True:
            # Refresh tag list in case it was updated
            self.tags = get_tags()
            
            # Calculate scroll offset if needed
            scroll_offset = 0
            if len(self.tags) > max_visible_tags:
                if self.current_idx >= max_visible_tags:
                    scroll_offset = min(self.current_idx - max_visible_tags + 1, len(self.tags) - max_visible_tags)
            
            # Clear tag display area
            for i in range(max_visible_tags):
                self.stdscr.addstr(tag_start_y + i, content_x, " " * (box_width - 4))
            
            # Display tags with selection status
            if not self.tags:
                self.stdscr.addstr(tag_start_y, content_x, "No tags found", curses.color_pair(8))
            else:
                visible_tags = self.tags[scroll_offset:scroll_offset + max_visible_tags]
                for i, tag in enumerate(visible_tags):
                    row = tag_start_y + i
                    actual_idx = i + scroll_offset
                    
                    # Determine attributes based on selection and current index
                    if actual_idx == self.current_idx:
                        attrs = curses.color_pair(3) | curses.A_REVERSE
                    elif tag in self.selected_tags:
                        attrs = curses.color_pair(10) | curses.A_BOLD
                    else:
                        attrs = curses.color_pair(9)
                    
                    # Show checkbox status
                    checkbox = symbols["checkbox_checked"] if tag in self.selected_tags else symbols["checkbox_empty"]
                    self.stdscr.addstr(row, content_x, checkbox + " ", curses.color_pair(4))
                    self.stdscr.addstr(row, content_x + 2, tag, attrs)
            
            # Scroll indicators if needed
            if len(self.tags) > max_visible_tags:
                if scroll_offset > 0:
                    self.stdscr.addstr(tag_start_y - 1, content_x + (box_width - 6) // 2, "▲ more", curses.color_pair(8))
                if scroll_offset + max_visible_tags < len(self.tags):
                    self.stdscr.addstr(tag_start_y + max_visible_tags, content_x + (box_width - 6) // 2, "▼ more", curses.color_pair(8))
            
            self.stdscr.refresh()
            key = self.stdscr.getch()
            
            if key in [ord('j'), curses.KEY_DOWN]:
                if self.tags:  # Only move if there are tags
                    self.current_idx = min(self.current_idx + 1, len(self.tags) - 1)
            elif key in [ord('k'), curses.KEY_UP]:
                if self.tags:  # Only move if there are tags
                    self.current_idx = max(self.current_idx - 1, 0)
            elif key == ord('a'):
                new_tag_text = self.get_user_input("Enter new tag: ")
                if new_tag_text:
                    new_tag(new_tag_text)
                    self.tags = get_tags()
                    self.draw_message(f"Tag '{new_tag_text}' added successfully", "success")
            elif key == ord(' '):  # Toggle selection
                if self.tags:
                    current_tag = self.tags[self.current_idx]
                    if current_tag in self.selected_tags:
                        self.selected_tags.remove(current_tag)
                    else:
                        self.selected_tags.add(current_tag)
            elif key == ord('q'):
                break

    def draw_add_menu(self):
        """Display the Add Menu for creating cards with tags."""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Calculate box dimensions
        box_height = 12
        box_width = 50
        start_y = (height - box_height) // 2
        start_x = (width - box_width) // 2
        
        # Draw border
        self.draw_border(start_y, start_x, box_height, box_width, "Add Menu")
        
        content_x = start_x + 4
        content_y = start_y + 3
        
        while True:
            # Display menu options - using two different colors
            self.stdscr.addstr(content_y, content_x, f"{symbols['card']} a", curses.color_pair(3))
            self.stdscr.addstr(content_y, content_x + 4, "- Create new card", curses.color_pair(2))
            
            self.stdscr.addstr(content_y + 1, content_x, f"{symbols['tag']} t", curses.color_pair(3))
            self.stdscr.addstr(content_y + 1, content_x + 4, "- Manage tags", curses.color_pair(2))
            
            self.stdscr.addstr(content_y + 2, content_x, f"{symbols['arrow']} q", curses.color_pair(3))
            self.stdscr.addstr(content_y + 2, content_x + 4, "- Return to main menu", curses.color_pair(2))
            
            # Draw horizontal separator
            self.stdscr.addstr(content_y + 4, start_x + 1, "─" * (box_width - 2), curses.color_pair(3))
            
            # Display currently selected tags
            self.stdscr.addstr(content_y + 5, content_x, "Selected Tags:", curses.color_pair(1) | curses.A_BOLD)
            if self.selected_tags:
                # Wrap tags if needed to fit the box width
                tag_str = ", ".join(self.selected_tags)
                max_tag_width = box_width - 8
                
                if len(tag_str) <= max_tag_width:
                    self.stdscr.addstr(content_y + 6, content_x, tag_str, curses.color_pair(10))
                else:
                    # Handle multi-line display if tags are too long
                    line = ""
                    line_y = 0
                    for tag in self.selected_tags:
                        if len(line) + len(tag) + 2 <= max_tag_width:
                            if line:
                                line += ", " + tag
                            else:
                                line = tag
                        else:
                            self.stdscr.addstr(content_y + 6 + line_y, content_x, line, curses.color_pair(10))
                            line_y += 1
                            line = tag
                    
                    if line:
                        self.stdscr.addstr(content_y + 6 + line_y, content_x, line, curses.color_pair(10))
            else:
                self.stdscr.addstr(content_y + 6, content_x, "None", curses.color_pair(8))
            
            self.stdscr.refresh()
            key = self.stdscr.getch()
            
            if key == ord('a'):
                self.create_card()  # Create a new card with current selected tags
                self.stdscr.clear()  # Clear screen after returning from card creation
            elif key == ord('t'):
                self.draw_manage_tags()  # Manage tags
                self.stdscr.clear()  # Clear screen after returning from tag management
            elif key == ord('q'):
                break  # Return to main menu

    def get_user_input(self, prompt: str) -> str:
        """Get text input from the user with a prompt."""
        # Save current terminal state
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Draw input box
        input_box_width = 50
        input_box_height = 5
        box_y = (height - input_box_height) // 2
        box_x = (width - input_box_width) // 2
        
        # Draw input box border
        self.draw_border(box_y, box_x, input_box_height, input_box_width, "Input")
        
        # Show prompt
        self.stdscr.addstr(box_y + 2, box_x + 3, prompt, curses.color_pair(2))
        self.stdscr.refresh()
        
        # Create input window for user text
        input_win = curses.newwin(1, input_box_width - 6 - len(prompt), box_y + 2, box_x + 3 + len(prompt))
        input_win.keypad(True)
        
        # Show cursor for input
        curses.curs_set(1)
        curses.echo()
        
        # Get input
        input_win.refresh()
        text = input_win.getstr().decode('utf-8')
        
        # Hide cursor again
        curses.noecho()
        curses.curs_set(0)
        
        return text

    def draw_main_menu(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Create box for main menu
        box_height = 12
        box_width = 40
        start_y = (height - box_height) // 2
        start_x = (width - box_width) // 2
        
        # Draw border with title
        self.draw_border(start_y, start_x, box_height, box_width, "Excalibur")
        
        # Update due cards count
        self.due_cards = get_cards_due()
        due_count = len(self.due_cards)
        
        # Draw cards due info
        due_info = f"Cards due today: {due_count}"
        due_x = start_x + (box_width - len(due_info)) // 2
        self.stdscr.addstr(start_y + 2, due_x, due_info, curses.color_pair(4) | curses.A_BOLD)
        
        # Draw separator
        self.stdscr.addstr(start_y + 3, start_x + 1, "─" * (box_width - 2), curses.color_pair(3))
        
        # Menu items with icons - using two different colors
        menu_items = [
            (f"{symbols['add']} a", "- Add new flashcard", 5),
            (f"{symbols['search']} s", "- Search cards", 6),
            (f"{symbols['review']} r", "- Review", 7),
            (f"{symbols['stats']} x", "- Statistics", 8),
            (f"{symbols['arrow']} q", "- Quit", 9)
        ]
        
        # Display menu items
        content_x = start_x + 4
        for i, (icon, text, line) in enumerate(menu_items):
            self.stdscr.addstr(start_y + 5 + i, content_x, icon, curses.color_pair(3))
            self.stdscr.addstr(start_y + 5 + i, content_x + 4, text, curses.color_pair(2))
        
        # Update status bar to show basic help
        self.status_bar.clear()
        self.status_bar.addstr(0, 1, " Press the highlighted key to select an option ", curses.color_pair(11))
        self.status_bar.refresh()

    def run(self):
        while True:
            # Update dimensions in case terminal was resized
            self.height, self.width = self.stdscr.getmaxyx()
            self.status_bar.resize(1, self.width)
            self.status_bar.mvwin(self.height-1, 0)
            
            self.draw_main_menu()
            key = self.stdscr.getch()
            
            if key == ord('q'):
                break
            elif key == ord('a'):
                self.draw_add_menu()
                self.stdscr.clear()  # Clear screen after returning from add menu
            elif key == ord('r'):
                # Review cards
                self.draw_review_ui()
                self.stdscr.clear() 

    def get_keypress(self):
        """ Get a keypress when curses is not active."""
        import sys
        import tty
        import termios
        
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

    def draw_review_ui(self):
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
            else:
                # Display back of card
                md = Markdown(back_content, justify="center")
                panel = Panel(md, border_style="none", expand=False, padding=(0, 2))
                console.print(Align.center(panel))
            
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
            
            # Don't show any status text at the bottom
            self.get_keypress()

        # Restore terminal state for curses
        curses.reset_prog_mode()
        self.stdscr.refresh()

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

def main(stdscr):
    ui = FlashcardUI(stdscr)
    ui.run()

if __name__ == "__main__":
    wrapper(main)

