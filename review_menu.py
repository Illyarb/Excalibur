import curses
import os
import copy
import datetime
import sys
import tty
import termios
from datetime import timedelta
from pathlib import Path
from typing import Dict, Set, List
import subprocess
import shutil
import time

from renderer import render_markdown

from base_ui import BaseUI
from config import db_path, colors, editor
from card_operations import (
    get_next_card_for_review, 
    load_card_content,
    review_card,
    get_all_cards_due,
    get_card_stats,
    get_card_by_id,
    delete_card,
    update_card
)
from db_operations import get_tags
from fsrs import Scheduler, Card, Rating, State


class ReviewMenu(BaseUI):
    def __init__(self, stdscr, selected_tags=None):
        super().__init__(stdscr)
        self.selected_tags = selected_tags if selected_tags is not None else set()
        self.terminal_mode = False
    
    def get_keypress(self):
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
    
    def format_time_diff(self, time_diff):
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
                next_dates[rating_value] = self.format_time_diff(time_diff)
            else:
                next_dates[rating_value] = "N/A"
        
        return next_dates

    def get_card_tags(self, card_id) -> Set[str]:
        import sqlite3
        from pathlib import Path
        from config import db_path
        
        conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
        c = conn.cursor()
        c.execute("SELECT tags FROM schedulling WHERE command = ?", (card_id,))
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            return set(tag.strip() for tag in result[0].split(',') if tag.strip())
        
        return set()
    
    def filter_due_cards_by_tags(self, due_cards) -> List[Dict]:
        if not self.selected_tags:
            return due_cards
        
        filtered_cards = []
        for card in due_cards:
            card_id = card["id"]
            card_tags = self.get_card_tags(card_id)
            
            if card_tags.intersection(self.selected_tags):
                filtered_cards.append(card)
        
        return filtered_cards
    
    def display_card(self, content, show_answer, card_id=None, next_review_dates=None):
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
            tags = self.get_card_tags(card_id)
        
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
        if not self.terminal_mode:
            curses.def_prog_mode()
            curses.endwin()
            self.terminal_mode = True
    
    def exit_terminal_mode(self):
        if self.terminal_mode:
            curses.reset_prog_mode()
            self.stdscr.refresh()
            self.terminal_mode = False

    def show_edit_menu(self, card_id, front_content, back_content):
            self.enter_terminal_mode()
            
            os.system('clear' if os.name == 'posix' else 'cls')
            
            terminal_width, terminal_height = os.get_terminal_size()
            
            padding_lines = terminal_height // 6
            for _ in range(padding_lines):
                print("")
            
            title = "Card Edit Menu"
            title_padding = (terminal_width - len(title)) // 2
            print(" " * title_padding + "\033[1;36m" + title + "\033[0m")
            print("")
            
            options = [
                ("f", "Edit front of card", "\033[33m"),
                ("b", "Edit back of card", "\033[33m"),
                ("p", "Edit card parameters", "\033[33m"),
                ("t", "Edit card tags", "\033[33m"),
                ("d", "Delete card", "\033[31m"),
                ("c", "Cancel and return to review", "\033[32m")
            ]
            
            for key, description, color in options:
                option_text = f"{key} - {description}"
                option_padding = (terminal_width - len(option_text)) // 2
                print(" " * option_padding + color + option_text + "\033[0m")
            
            print("")
            prompt = "Press a key to select an option:"
            prompt_padding = (terminal_width - len(prompt)) // 2
            print(" " * prompt_padding + "\033[1m" + prompt + "\033[0m")
            
            card_deleted = False
            
            while True:
                key = self.get_keypress()
                
                if key == 'f':
                    self.edit_card_content(card_id, "front", front_content)
                    break
                elif key == 'b':
                    self.edit_card_content(card_id, "back", back_content)
                    break
                elif key == 'p':
                    self.edit_card_parameters(card_id)
                    break
                elif key == 't':
                    self.edit_card_tags(card_id)
                    break
                elif key == 'd':
                    if self.confirm_delete_card(card_id):
                        card_deleted = True
                    break
                elif key == 'c' or key == 'q':
                    break
            
            return card_deleted

    def edit_card_content(self, card_id, side, current_content):
        from pathlib import Path
        from config import db_path, editor
        
        file_path = Path(db_path + f"/cards/{card_id}_{side}.md").expanduser()
        
        if not file_path.exists():
            with open(file_path, 'w') as f:
                f.write(current_content)
        
        try:
            subprocess.run([editor, str(file_path)])
        except Exception as e:
            fallback_editors = ['nano', 'vim', 'vi', 'notepad']
            for fallback in fallback_editors:
                try:
                    subprocess.run([fallback, str(file_path)])
                    break
                except Exception:
                    continue
        
        return

    def edit_card_tags(self, card_id):
        from manage_tags_menu import ManageTagsMenu
        
        current_tags = self.get_card_tags(card_id)
        
        # Exit terminal mode temporarily to use curses for tag menu
        self.exit_terminal_mode()
        
        self.stdscr.clear()
        tag_menu = ManageTagsMenu(self.stdscr, selected_tags=current_tags)
        new_tags = tag_menu.run()
        
        # Return to terminal mode after tag menu finishes
        self.enter_terminal_mode()
        
        if new_tags is not None and new_tags != current_tags:
            tags_str = ','.join(new_tags)
            
            import sqlite3
            conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
            c = conn.cursor()
            c.execute("UPDATE schedulling SET tags = ? WHERE command = ?", (tags_str, card_id))
            conn.commit()
            conn.close()

    def edit_card_parameters(self, card_id):
        card = get_card_by_id(card_id)
        if not card:
            return
        
        os.system('clear' if os.name == 'posix' else 'cls')
        
        terminal_width, terminal_height = os.get_terminal_size()
        
        padding_lines = terminal_height // 8
        for _ in range(padding_lines):
            print("")
        
        title = "Edit Card Parameters"
        title_padding = (terminal_width - len(title)) // 2
        print(" " * title_padding + "\033[1;36m" + title + "\033[0m")
        print("")
        
        values = [
            f"Current Difficulty: {card.difficulty:.2f}",
            f"Current Stability: {card.stability:.2f}",
            f"Current State: {card.state.name if card.state else 'NEW'}",
            f"Current Due Date: {card.due.strftime('%Y-%m-%d %H:%M') if card.due else 'Not set'}"
        ]
        
        for value in values:
            value_padding = (terminal_width - len(value)) // 2
            print(" " * value_padding + "\033[33m" + value + "\033[0m")
        
        print("")
        
        instr = "Enter new values (leave blank to keep current value)"
        instr_padding = (terminal_width - len(instr)) // 2
        print(" " * instr_padding + "\033[36m" + instr + "\033[0m")
        print("")
        
        def get_input(prompt, default=""):
            prompt_padding = (terminal_width - len(prompt)) // 2
            print(" " * prompt_padding + "\033[1m" + prompt + "\033[0m")
            padding = (terminal_width - 30) // 2
            print(" " * padding, end="")
            return input() or default
        
        try:
            new_difficulty = get_input(f"New Difficulty (0.0-10.0) [{card.difficulty:.2f}]: ", str(card.difficulty))
            try:
                card.difficulty = float(new_difficulty)
                card.difficulty = max(0.0, min(10.0, card.difficulty))
            except ValueError:
                pass
            
            new_stability = get_input(f"New Stability (>= 0.0) [{card.stability:.2f}]: ", str(card.stability))
            try:
                card.stability = float(new_stability)
                card.stability = max(0.0, card.stability)
            except ValueError:
                pass
            
            states_info = "States: 0=NEW, 1=LEARNING, 2=REVIEW, 3=RELEARNING"
            states_padding = (terminal_width - len(states_info)) // 2
            print(" " * states_padding + "\033[36m" + states_info + "\033[0m")
            
            new_state = get_input(f"New State (0-3) [{card.state.value if card.state else 0}]: ", 
                                 str(card.state.value if card.state else 0))
            try:
                state_value = int(new_state)
                if 0 <= state_value <= 3:
                    card.state = State(state_value)
            except (ValueError, TypeError):
                pass
            
            date_info = "Format: YYYY-MM-DD HH:MM (e.g., 2023-12-31 14:30)"
            date_padding = (terminal_width - len(date_info)) // 2
            print(" " * date_padding + "\033[36m" + date_info + "\033[0m")
            
            due_date = card.due.strftime("%Y-%m-%d %H:%M") if card.due else "Not set"
            new_due_date = get_input(f"New Due Date [{due_date}]: ", due_date)
            
            if new_due_date != "Not set":
                try:
                    card.due = datetime.datetime.strptime(new_due_date, "%Y-%m-%d %H:%M")
                    card.due = card.due.replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    error_msg = "Invalid date format. Keeping current value."
                    error_padding = (terminal_width - len(error_msg)) // 2
                    print(" " * error_padding + "\033[31m" + error_msg + "\033[0m")
                    prompt = "Press any key to continue..."
                    prompt_padding = (terminal_width - len(prompt)) // 2
                    print(" " * prompt_padding + "\033[1m" + prompt + "\033[0m")
                    self.get_keypress()
            
            update_card(card_id, card)
            
            print("")
            success_msg = "Parameters updated successfully!"
            success_padding = (terminal_width - len(success_msg)) // 2
            print(" " * success_padding + "\033[1;32m" + success_msg + "\033[0m")
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            error_padding = (terminal_width - len(error_msg)) // 2
            print(" " * error_padding + "\033[1;31m" + error_msg + "\033[0m")
        
        print("")
        prompt = "Press any key to return..."
        prompt_padding = (terminal_width - len(prompt)) // 2
        print(" " * prompt_padding + "\033[1m" + prompt + "\033[0m")
        self.get_keypress()

    def confirm_delete_card(self, card_id):
        os.system('clear' if os.name == 'posix' else 'cls')
        
        terminal_width, terminal_height = os.get_terminal_size()
        
        padding_lines = terminal_height // 3
        for _ in range(padding_lines):
            print("")
        
        warning = "⚠️  WARNING: You are about to delete this card  ⚠️"
        warning_padding = (terminal_width - len(warning)) // 2
        print(" " * warning_padding + "\033[1;31m" + warning + "\033[0m")
        print("")
        
        prompt = "Are you sure? This action cannot be undone. (y/n)"
        prompt_padding = (terminal_width - len(prompt)) // 2
        print(" " * prompt_padding + "\033[33m" + prompt + "\033[0m")
        
        success = False
        
        while True:
            key = self.get_keypress()
            
            if key.lower() == 'y':
                success = delete_card(card_id)
                
                print("")
                if success:
                    result = "Card deleted successfully."
                    print(" " * ((terminal_width - len(result)) // 2) + "\033[32m" + result + "\033[0m")
                else:
                    result = "Failed to delete card!"
                    print(" " * ((terminal_width - len(result)) // 2) + "\033[31m" + result + "\033[0m")
                
                print("")
                wait_prompt = "Press any key to continue..."
                print(" " * ((terminal_width - len(wait_prompt)) // 2) + "\033[1m" + wait_prompt + "\033[0m")
                self.get_keypress()
                break
            elif key.lower() == 'n' or key == '\x1b':
                break
        
        return success
                
    def draw_review_stats(self, card_id):
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
        
        card_tags = self.get_card_tags(card_id)
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
        due_cards = get_all_cards_due()

        if not due_cards:
            self.draw_message("No cards due for review!", "info")
            return

        if self.selected_tags:
            due_cards = self.filter_due_cards_by_tags(due_cards)
            
        if not due_cards:
            self.draw_message("No cards due for selected tags!", "info")
            return

        current_card_idx = 0
        show_answer = False
        exit_review = False

        # Enter terminal mode for review
        self.enter_terminal_mode()

        while not exit_review and current_card_idx < len(due_cards):
            try:
                card = due_cards[current_card_idx]
                card_id = card["id"]
                front_content = card["front"]
                back_content = card["back"]
                
                next_review_dates = self.calculate_next_review_dates(card_id)
                
                content = front_content if not show_answer else back_content
                self.display_card(
                    content=content, 
                    show_answer=show_answer, 
                    card_id=card_id,
                    next_review_dates=next_review_dates if show_answer else None
                )
                
                key = self.get_keypress()
                
                if key == 'e':
                    card_deleted = self.show_edit_menu(card_id, front_content, back_content)
                    
                    if card_deleted:
                        due_cards.pop(current_card_idx)
                        
                        if not due_cards:
                            exit_review = True
                        continue
                    
                    updated_front, updated_back = load_card_content(card_id)
                    if updated_front:
                        due_cards[current_card_idx]["front"] = updated_front
                        front_content = updated_front
                    if updated_back:
                        due_cards[current_card_idx]["back"] = updated_back
                        back_content = updated_back
                    
                    if self.selected_tags:
                        card_tags = self.get_card_tags(card_id)
                        if not card_tags.intersection(self.selected_tags):
                            due_cards.pop(current_card_idx)
                            if not due_cards:
                                exit_review = True
                            continue
                    
                    continue
                elif not show_answer and key in ('h', ' ', 'KEY_RIGHT'):
                    show_answer = True
                elif show_answer and key == ' ':
                    show_answer = False
                elif show_answer and key in ('l', 'k', 'j', 'h'):
                    rating_map = {
                        'l': 1,  # Again
                        'k': 2,  # Hard
                        'j': 3,  # Good
                        'h': 4,  # Easy
                    }
                    
                    review_card(card_id, rating_map[key])
                    
                    current_card_idx += 1
                    show_answer = False
                elif key == 'q':
                    exit_review = True
            except Exception as e:
                error_msg = f"Error: {e}"
                print("\033[31m" + error_msg + "\033[0m")
                time.sleep(2)

        if current_card_idx >= len(due_cards) and not exit_review:
            os.system('clear' if os.name == 'posix' else 'cls')
            
            terminal_width, terminal_height = os.get_terminal_size()
            
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

        # Exit terminal mode and return to curses mode
        self.exit_terminal_mode()

