import os
import sys
import tty
import termios
import time
import shutil
import curses
from pathlib import Path

from utils.renderer import render_markdown
from ui.base_ui import BaseUI
from operations.card_operations import (
    get_all_cards_due,
    review_card,
    load_card_content,
    calculate_next_review_dates,
    filter_due_cards_by_tags, 
    get_card_stats
)
from operations.db_operations import get_tags, get_card_tags
from ui.edit_menu import EditMenu  

class ReviewMenu(BaseUI):
    def __init__(self, stdscr, selected_tags=None):
        super().__init__(stdscr)
        self.selected_tags = selected_tags if selected_tags is not None else set()
        self.terminal_mode = False
    
    def get_keypress(self):
        """Get a single keypress from the user in terminal mode"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            
            if ch == '\x1b':
                ch += sys.stdin.read(2)
                
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
    
    def display_card(self, content, show_answer, card_id=None, next_review_dates=None):
        """Display a flashcard in the terminal"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        try:
            terminal_width, terminal_height = shutil.get_terminal_size()
        except (AttributeError, ValueError, OSError):
            terminal_width, terminal_height = 80, 24
        
        if content is None:
            content = ""
        elif isinstance(content, list):
            content = "\n".join(str(line) for line in content)
        else:
            content = str(content)
        
        try:
            rendered_content = render_markdown(content, colored_output=True, centered=True)
        except Exception as e:
            rendered_content = content
            print(f"\033[31mError rendering content: {str(e)}\033[0m")
        
        content_lines = rendered_content.splitlines()
        
        tags = set()
        if card_id:
            tags = get_card_tags(card_id)
        
        reserved_lines = 2 if show_answer else 1
        
        max_lines = terminal_height - reserved_lines
        visible_lines = min(len(content_lines), max_lines)
        
        for i in range(visible_lines):
            print(content_lines[i])
        
        if terminal_height > visible_lines + 1:
            for _ in range(terminal_height - visible_lines - 1):
                print("")
        
        if tags:
            tags_str = ", ".join(tags)
            print(f"\033[38;5;240m{tags_str}\033[0m".ljust(terminal_width))
        
        if show_answer and next_review_dates:
            again_str = f"Again(l) - {next_review_dates[1]}"
            hard_str = f"Hard(k) - {next_review_dates[2]}"
            good_str = f"Good(j) - {next_review_dates[3]}"
            easy_str = f"Easy(h) - {next_review_dates[4]}"
            
            status_text = f"{easy_str} | {good_str} | {hard_str} | {again_str}"
            
            padding = (terminal_width - len(status_text)) // 2
            
            print(f"\033[{terminal_height};1H", end="")
            print("\033[2K", end="")
            
            print(" " * padding, end="")
            
            print(f"\033[36m{easy_str}\033[0m", end="")
            print(" | ", end="")
            
            print(f"\033[32m{good_str}\033[0m", end="")
            print(" | ", end="")
            
            print(f"\033[33m{hard_str}\033[0m", end="")
            print(" | ", end="")
            
            print(f"\033[31m{again_str}\033[0m", end="")
            
            print(f"\033[1;1H", end="")
            sys.stdout.flush()
    
    def enter_terminal_mode(self):
        """Switch from curses to terminal mode"""
        if not self.terminal_mode:
            curses.def_prog_mode()
            curses.endwin()
            self.terminal_mode = True
    
    def exit_terminal_mode(self):
        """Switch from terminal back to curses mode"""
        if self.terminal_mode:
            curses.reset_prog_mode()
            self.stdscr.refresh()
            self.terminal_mode = False
    
    def show_completion_message(self):
        """Display completion message when all cards are reviewed"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        terminal_width, terminal_height = shutil.get_terminal_size()
        padding_lines = terminal_height // 3
        
        for _ in range(padding_lines):
            print("")
        
        if self.selected_tags and len(self.selected_tags) < len(get_tags()):
            tag_list = ", ".join(self.selected_tags)
            completion_message = f"Congratulations! You've completed all due cards for tags: {tag_list}"
        else:
            completion_message = "Congratulations! You've completed all due cards!"
            
        padding = (terminal_width - len(completion_message)) // 2
        print(" " * padding + "\033[1;32m" + completion_message + "\033[0m")
        
        self.get_keypress()

    def show_stats(self, card_id):
        """Display card statistics in curses mode"""
        stats = get_card_stats(card_id)
        
        if not stats:
            return
        
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        box_height = 14
        box_width = 50
        start_y = (height - box_height) // 2
        start_x = (width - box_width) // 2
        
        self.draw_border(start_y, start_x, box_height, box_width, "Card Statistics")
        
        content_x = start_x + 4
        content_y = start_y + 3
        
        due_str = "N/A"
        if stats["due"]:
            due_str = stats["due"].strftime("%Y-%m-%d %H:%M")
        
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
        
        if stats["retrievability"] is not None:
            self.stdscr.addstr(content_y + 6, content_x, "Retrievability: ", curses.color_pair(3))
            
            retrievability_str = f"{stats['retrievability']}%"
            if stats["retrievability"] >= 90:
                attr = curses.color_pair(7)
            elif stats["retrievability"] >= 70:
                attr = curses.color_pair(9)
            else:
                attr = curses.color_pair(6)
            
            self.stdscr.addstr(content_y + 6, content_x + 15, retrievability_str, attr)
        
        card_tags = get_card_tags(card_id)
        if card_tags:
            self.stdscr.addstr(content_y + 8, content_x, "Tags: ", curses.color_pair(3))
            tags_str = ", ".join(card_tags)
            if len(tags_str) > box_width - 10:
                tags_str = tags_str[:box_width - 13] + "..."
            self.stdscr.addstr(content_y + 8, content_x + 6, tags_str, curses.color_pair(9))
        
        self.stdscr.addstr(content_y + 10, content_x, "Press any key to continue...", curses.color_pair(8))
        self.stdscr.refresh()
        self.stdscr.getch()

    def run(self):
        """Main function to run the review menu"""
        # Get all due cards
        due_cards = get_all_cards_due()

        if not due_cards:
            self.draw_message("No cards due for review!", "info")
            return

        # Filter cards by selected tags if any
        if self.selected_tags:
            due_cards = filter_due_cards_by_tags(due_cards, self.selected_tags)
            
        if not due_cards:
            self.draw_message("No cards due for selected tags!", "info")
            return

        # Initialize variables
        current_card_idx = 0
        show_answer = False
        exit_review = False

        # Enter terminal mode for review
        self.enter_terminal_mode()

        # Create edit menu
        edit_menu = EditMenu(self.stdscr)

        while not exit_review and current_card_idx < len(due_cards):
            try:
                # Get current card info
                card = due_cards[current_card_idx]
                card_id = card["id"]
                front_content = card["front"]
                back_content = card["back"]
                
                # Calculate next review dates
                next_review_dates = calculate_next_review_dates(card_id)
                
                # Display card content
                content = front_content if not show_answer else back_content
                self.display_card(
                    content=content, 
                    show_answer=show_answer, 
                    card_id=card_id,
                    next_review_dates=next_review_dates if show_answer else None
                )
                
                # Handle user input
                key = self.get_keypress()
                
                if key == 'e':
                    # Exit terminal mode temporarily to show edit menu
                    self.exit_terminal_mode()
                    card_deleted = edit_menu.show_edit_menu(card_id, front_content, back_content)
                    self.enter_terminal_mode()
                    
                    if card_deleted:
                        due_cards.pop(current_card_idx)
                        if not due_cards:
                            exit_review = True
                        continue
                    
                    # Reload card content in case it was edited
                    updated_front, updated_back = load_card_content(card_id)
                    if updated_front:
                        due_cards[current_card_idx]["front"] = updated_front
                        front_content = updated_front
                    if updated_back:
                        due_cards[current_card_idx]["back"] = updated_back
                        back_content = updated_back
                    
                    # Check if card still matches tag filter
                    if self.selected_tags:
                        card_tags = get_card_tags(card_id)
                        if not card_tags.intersection(self.selected_tags):
                            due_cards.pop(current_card_idx)
                            if not due_cards:
                                exit_review = True
                            continue
                    
                    continue
                
                elif key == 's':  # Show stats
                    self.exit_terminal_mode()
                    self.show_stats(card_id)
                    self.enter_terminal_mode()
                    
                elif not show_answer and key in ('h', ' ', 'KEY_RIGHT'):
                    # Show answer
                    show_answer = True
                    
                elif show_answer and key == ' ':
                    # Hide answer
                    show_answer = False
                    
                elif show_answer and key in ('l', 'k', 'j', 'h'):
                    # Process rating
                    rating_map = {
                        'l': 1,  # Again
                        'k': 2,  # Hard
                        'j': 3,  # Good
                        'h': 4,  # Easy
                    }
                    
                    # Update card with rating
                    review_card(card_id, rating_map[key])
                    
                    # Move to next card
                    current_card_idx += 1
                    show_answer = False
                    
                elif key == 'q':
                    # Exit review
                    exit_review = True
                    
            except Exception as e:
                error_msg = f"Error: {e}"
                print("\033[31m" + error_msg + "\033[0m")
                time.sleep(2)

        # Show completion message if all cards reviewed
        if current_card_idx >= len(due_cards) and not exit_review:
            self.show_completion_message()

        # Exit terminal mode and return to curses mode
        self.exit_terminal_mode()
