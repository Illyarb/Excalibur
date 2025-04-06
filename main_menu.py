import curses
from typing import Dict, List, Set

from base_ui import BaseUI
from config import symbols
from db_operations import get_cards_due, get_tags
from card_operations import get_cards_by_tag
from review_menu import ReviewMenu
from add_menu import AddMenu


class MainMenu(BaseUI):
    def __init__(self, stdscr):
        super().__init__(stdscr)
        self.due_cards = get_cards_due()
        self.tags = get_tags()
        self.tag_due_counts = self.get_tag_due_counts()
        self.selected_tags = set(self.tags)
        self.selected_tag_idx = 0
        self.show_tag_menu = False
    
    def get_tag_due_counts(self) -> Dict[str, int]:
        tag_counts = {}
        
        for tag in self.tags:
            tag_counts[tag] = 0
        
        for card_id in self.due_cards:
            card_tags = self.get_card_tags(card_id)
            for tag in card_tags:
                tag = tag.strip()
                if tag in tag_counts:
                    tag_counts[tag] += 1
        
        return tag_counts
    
    def get_card_tags(self, card_id) -> List[str]:
        import sqlite3
        from pathlib import Path
        from config import db_path
        
        conn = sqlite3.connect(Path(db_path + "/excalibur.db").expanduser())
        c = conn.cursor()
        c.execute("SELECT tags FROM schedulling WHERE command = ?", (card_id,))
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            return [tag.strip() for tag in result[0].split(',') if tag.strip()]
        
        return []
    
    def get_due_cards_for_selected_tags(self) -> List[str]:
        if not self.selected_tags:
            return []
        
        if set(self.tags) == self.selected_tags:
            return self.due_cards
        
        filtered_cards = []
        for card_id in self.due_cards:
            card_tags = self.get_card_tags(card_id)
            
            # More robust tag matching - normalize by stripping whitespace
            normalized_card_tags = [tag.strip() for tag in card_tags]
            normalized_selected_tags = [tag.strip() for tag in self.selected_tags]
            
            if any(tag in normalized_selected_tags for tag in normalized_card_tags):
                filtered_cards.append(card_id)
        
        return filtered_cards
    
    def draw_main_menu(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        box_height = 16  
        box_width = 60   
        start_y = (height - box_height) // 2
        start_x = (width - box_width) // 2
        
        self.draw_border(start_y, start_x, box_height, box_width, "Excalibur")
        self.due_cards = get_cards_due()
        self.tags = get_tags()
        self.tag_due_counts = self.get_tag_due_counts()
        due_count = len(self.due_cards)
        filtered_due_count = len(self.get_due_cards_for_selected_tags())
        
        due_info = f"Cards due: {filtered_due_count}"
        due_x = start_x + (box_width - len(due_info)) // 2
        self.stdscr.addstr(start_y + 2, due_x, due_info, curses.color_pair(4) | curses.A_BOLD)
        
        tag_info = f"Selected tags: {len(self.selected_tags)}/{len(self.tags)}"
        tag_x = start_x + (box_width - len(tag_info)) // 2
        self.stdscr.addstr(start_y + 3, tag_x, tag_info, curses.color_pair(9))
        
        self.stdscr.addstr(start_y + 4, start_x + 1, "─" * (box_width - 2), curses.color_pair(3))
        
        if self.show_tag_menu:
            self.draw_tag_selection(start_y + 5, start_x + 2, box_width - 4)
            self.stdscr.addstr(start_y + 12, start_x + 1, "─" * (box_width - 2), curses.color_pair(3))
            menu_start_y = start_y + 13
        else:
            menu_start_y = start_y + 6
        
        menu_items = [
            (f"{symbols['add']} a", "- Add new flashcard", 5),
            (f"{symbols['search']} s", "- Search cards", 6),
            (f"{symbols['review']} r", "- Review", 7),
            (f"{symbols['stats']} x", "- Statistics", 8),
            (f"{symbols['arrow']} q", "- Quit", 9),
            (f"{symbols['tag'] if 'tag' in symbols else '#'} t", f"- {'Hide' if self.show_tag_menu else 'Show'} tags", 9)
        ]
        
        content_x = start_x + 4
        for i, (icon, text, color) in enumerate(menu_items):
            row = i % 3
            col = i // 3
            col_offset = col * 25
            self.stdscr.addstr(menu_start_y + row, content_x + col_offset, icon, curses.color_pair(3))
            self.stdscr.addstr(menu_start_y + row, content_x + col_offset + 4, text, curses.color_pair(2))
        
        self.status_bar.clear()
    
    def draw_tag_selection(self, start_y, start_x, width):
        max_visible = 6
        
        if not self.tags:
            self.stdscr.addstr(start_y, start_x, "No tags available.", curses.color_pair(8))
            return
        
        start_idx = max(0, min(self.selected_tag_idx - max_visible // 2, len(self.tags) - max_visible))
        end_idx = min(start_idx + max_visible, len(self.tags))
        
        header = f"{'Tag':<20} {'Due':>5} {'Selected':<10}"
        self.stdscr.addstr(start_y, start_x, header, curses.color_pair(1) | curses.A_BOLD)
        start_y += 1
        
        for i, tag in enumerate(self.tags[start_idx:end_idx], start_idx):
            if i == self.selected_tag_idx:
                style = curses.color_pair(3) | curses.A_BOLD
            else:
                style = curses.color_pair(2)
            
            tag_display = tag[:18] + ".." if len(tag) > 20 else tag.ljust(20)
            
            due_count = self.tag_due_counts.get(tag.strip(), 0)
            
            checkbox = "[✓]" if tag in self.selected_tags else "[ ]"
            
            row = f"{tag_display} {due_count:5d} {checkbox}"
            self.stdscr.addstr(start_y + i - start_idx, start_x, row, style)
        
        if self.tags:
            instructions = [
                "j/↓ - Move down",
                "k/↑ - Move up",
                "Space - Toggle selection",
                "a - Select all",
                "n - Select none"
            ]
            
            inst_y = start_y + max_visible + 1
            for i, instruction in enumerate(instructions):
                if i < 3:
                    inst_y += 1
                else:
                    self.stdscr.addstr(inst_y - 3, start_x + width // 2, instruction, curses.color_pair(8))

    def run(self):
        while True:
            self.update_dimensions()
            
            self.draw_main_menu()
            
            key = self.stdscr.getch()
            
            if key == ord('q'):
                break
            elif key == ord('a'):
                add_menu = AddMenu(self.stdscr)
                add_menu.run()
                self.stdscr.clear()
            elif key == ord('r'):
                filtered_due_cards = self.get_due_cards_for_selected_tags()

                if not filtered_due_cards:
                    self.draw_message("No cards due for selected tags!", "info")
                    continue

                review_menu = ReviewMenu(self.stdscr, selected_tags=self.selected_tags)
                review_menu.run()
                self.stdscr.clear()

            elif key == ord('s'):
                self.draw_message("Search functionality coming soon!", "info")
            elif key == ord('x'):
                self.draw_message("Statistics functionality coming soon!", "info")
            elif key == ord('t'):
                self.show_tag_menu = not self.show_tag_menu

            elif self.show_tag_menu:
                if key == ord('j') or key == curses.KEY_DOWN:
                    self.selected_tag_idx = min(len(self.tags) - 1, self.selected_tag_idx + 1)
                elif key == ord('k') or key == curses.KEY_UP:
                    self.selected_tag_idx = max(0, self.selected_tag_idx - 1)
                elif key == ord(' '):
                    if self.tags and 0 <= self.selected_tag_idx < len(self.tags):
                        tag = self.tags[self.selected_tag_idx]
                        if tag in self.selected_tags:
                            self.selected_tags.remove(tag)
                        else:
                            self.selected_tags.add(tag)
                elif key == ord('a'):
                    self.selected_tags = set(self.tags)
                elif key == ord('n'):
                        self.selected_tags = set()


def main(stdscr):
    ui = MainMenu(stdscr)
    ui.run()


if __name__ == "__main__":
    curses.wrapper(main)
