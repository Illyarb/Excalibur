import curses
from curses import wrapper
from typing import List, Set
from db_operations import new_tag, get_tags, add_card
import subprocess
import os
from pathlib import Path
from config import db_path
import uuid

class FlashcardUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.tags = get_tags()
        self.selected_tags: Set[str] = set()
        curses.curs_set(0)
        curses.use_default_colors()
        self.current_idx = 0

    def create_card(self):
        card_id = str(uuid.uuid4())
        scripts_dir = Path(db_path + "/scripts").expanduser()
        
        # Create front of card
        front_path = scripts_dir / f"{card_id}_front.md"
        subprocess.run(["nvim", str(front_path)])
        
        # Create back of card
        back_path = scripts_dir / f"{card_id}_back.md"
        subprocess.run(["nvim", str(back_path)])
        
        if front_path.exists() and back_path.exists():
            add_card(card_id, ",".join(self.selected_tags))
            height, width = self.stdscr.getmaxyx()
            self.stdscr.addstr(height-2, 2, "Card added successfully!")
            self.stdscr.refresh()
            curses.napms(1000)

    def draw_tag_management(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        start_y = height // 2 - len(self.tags) // 2
        start_x = width // 2 - 15

        self.stdscr.addstr(start_y - 2, start_x, "Tag Management", curses.A_BOLD)
        self.stdscr.addstr(start_y - 1, start_x, "j/k: move, a: add new, space: select, q: back")

        while True:
            for i, tag in enumerate(self.tags):
                attrs = curses.A_REVERSE if i == self.current_idx else 0
                if tag in self.selected_tags:
                    attrs |= curses.A_BOLD
                self.stdscr.addstr(start_y + i, start_x, tag, attrs)

            key = self.stdscr.getch()
            
            if key in [ord('j'), curses.KEY_DOWN]:
                self.current_idx = min(self.current_idx + 1, len(self.tags) - 1)
            elif key in [ord('k'), curses.KEY_UP]:
                self.current_idx = max(self.current_idx - 1, 0)
            elif key == ord('a'):
                new_tag_text = self.get_user_input("Enter new tag: ")
                if new_tag_text:
                    new_tag(new_tag_text)
                    self.tags = get_tags()
            elif key == ord(' '):
                current_tag = self.tags[self.current_idx]
                if current_tag in self.selected_tags:
                    self.selected_tags.remove(current_tag)
                else:
                    self.selected_tags.add(current_tag)
            elif key == ord('q'):
                break

    def get_user_input(self, prompt: str) -> str:
        self.stdscr.addstr(2, 2, prompt)
        curses.echo()
        curses.curs_set(1)
        input_win = curses.newwin(1, 30, 3, 2)
        input_win.refresh()
        text = input_win.getstr().decode('utf-8')
        curses.noecho()
        curses.curs_set(0)
        return text

    def draw_main_menu(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        start_y = height // 2 - 4
        start_x = width // 2 - 15
        
        self.stdscr.addstr(start_y, start_x, "📚 Flashcards", curses.A_BOLD)
        self.stdscr.addstr(start_y + 1, start_x, "Cards due today: 5")
        
        menu_items = [
            "a - Add new flashcard",
            "t - Add new tag",
            "s - Search cards",
            "r - Review",
            "x - Statistics",
            "q - Quit"
        ]
        
        for i, item in enumerate(menu_items):
            self.stdscr.addstr(start_y + 3 + i, start_x, item)

        self.stdscr.refresh()

    def run(self):
        while True:
            self.draw_main_menu()
            key = self.stdscr.getch()
            
            if key == ord('q'):
                break
            elif key == ord('t'):
                self.draw_tag_management()
            elif key == ord('a'):
                self.create_card()

def main(stdscr):
    ui = FlashcardUI(stdscr)
    ui.run()

if __name__ == "__main__":
    wrapper(main)
