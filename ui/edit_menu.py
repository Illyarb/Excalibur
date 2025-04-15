import os
import sys
import tty
import termios
import shutil
import subprocess
import datetime
import curses
from pathlib import Path

from ui.base_ui import BaseUI
from operations.card_operations import (
    update_card_content,
    delete_card,
    get_card_by_id,
    update_card,
    get_card_stats
)
from operations.db_operations import get_card_tags, update_card_tags
from config import db_path, editor
from fsrs import State

class EditMenu(BaseUI):
    def __init__(self, stdscr):
        super().__init__(stdscr)
        self.terminal_mode = False
        
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

    def show_edit_menu(self, card_id, front_content, back_content):
        self.enter_terminal_mode()
        
        os.system('clear' if os.name == 'posix' else 'cls')
        
        terminal_width, terminal_height = shutil.get_terminal_size()
        
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
        
        with open(file_path, 'r') as f:
            new_content = f.read()
        update_card_content(card_id, side, new_content)
        return

    def edit_card_tags(self, card_id):
        from manage_tags_menu import ManageTagsMenu
        
        current_tags = get_card_tags(card_id)
        
        self.exit_terminal_mode()
        
        self.stdscr.clear()
        tag_menu = ManageTagsMenu(self.stdscr, selected_tags=current_tags)
        new_tags = tag_menu.run()
        
        self.enter_terminal_mode()
        
        if new_tags is not None and new_tags != current_tags:
            update_card_tags(card_id, new_tags)

    def edit_card_parameters(self, card_id):
        card = get_card_by_id(card_id)
        if not card:
            return
        
        os.system('clear' if os.name == 'posix' else 'cls')
        
        terminal_width, terminal_height = shutil.get_terminal_size()
        
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
        
        terminal_width, terminal_height = shutil.get_terminal_size()
        
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
