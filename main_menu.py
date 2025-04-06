import curses
import datetime
import math
from typing import Dict, List, Set

from base_ui import BaseUI
from config import symbols
import db_operations
from card_operations import get_cards_by_tag, get_due_count
from review_menu import ReviewMenu
from add_menu import AddMenu
from statistics import (
    get_review_history_by_day,
    get_cards_due_next_days,
    get_advanced_stats,
    draw_heatmap,
    draw_calendar,
    draw_statistics
)


class MainMenu(BaseUI):
    def __init__(self, stdscr):
        super().__init__(stdscr)
        self.due_cards = db_operations.get_cards_due()
        self.tags = db_operations.get_tags()
        self.tag_due_counts = db_operations.get_tag_due_counts()
        self.selected_tags = set(self.tags)
        self.menu_items = [
            ("Add new flashcard", 'a'),
            ("Search cards", 's'),
            ("Review", 'r'),
            ("Toggle tag selection", 't'),
            ("Quit", 'q')
        ]
        self.selected_menu_idx = 0
        self.selected_tag_idx = 0
        self.tag_section_active = False
        
        self.review_counts = get_review_history_by_day()
        self.due_counts = get_cards_due_next_days()
        self.stats = get_advanced_stats()
        
        self.needs_full_redraw = True
        
        curses.start_color()
        curses.use_default_colors()
        for i in range(curses.COLORS):
            curses.init_pair(i, i, -1)
    
    def refresh_data(self):
        self.due_cards = db_operations.get_cards_due()
        self.tags = db_operations.get_tags()
        self.tag_due_counts = db_operations.get_tag_due_counts()
        self.review_counts = get_review_history_by_day()
        self.due_counts = get_cards_due_next_days()
        self.stats = get_advanced_stats()
        self.needs_full_redraw = True
    
    def draw_safe_border(self, y, x, height, width, title=None):
        max_height, max_width = self.stdscr.getmaxyx()
        
        if y + height >= max_height:
            height = max_height - y - 1
        
        if x + width >= max_width:
            width = max_width - x - 1
            
        self.stdscr.addstr(y, x, "╭" + "─" * (width - 2) + "╮", curses.color_pair(3))
        
        for i in range(1, height - 1):
            self.stdscr.addstr(y + i, x, "│", curses.color_pair(3))
            self.stdscr.addstr(y + i, x + width - 1, "│", curses.color_pair(3))
        
        try:
            self.stdscr.addstr(y + height - 1, x, "╰" + "─" * (width - 2) + "╯", curses.color_pair(3))
        except curses.error:
            self.stdscr.addstr(y + height - 1, x, "╰" + "─" * (width - 2), curses.color_pair(3))
        
        if title:
            title = f" {title} "
            title_x = x + (width - len(title)) // 2
            self.stdscr.addstr(y, title_x, title, curses.color_pair(1) | curses.A_BOLD)

    def draw_main_menu(self):
        if self.needs_full_redraw:
            self.stdscr.clear()
            self.needs_full_redraw = False
        
        height, width = self.stdscr.getmaxyx()
        
        self.draw_safe_border(0, 0, height, width, "Excalibur Flashcards")
        
        menu_width = 30
        stats_width = width - menu_width - 3
        
        for y in range(1, height - 1):
            self.stdscr.addstr(y, menu_width, "│", curses.color_pair(3))
        
        self.draw_menu_section(1, 1, menu_width - 1, height - 2)
        
        self.draw_statistics_section(1, menu_width + 1, stats_width, height - 2)
        
        self.status_bar.clear()
    
    def draw_menu_section(self, start_y, start_x, width, height):
        filtered_due_count = len(db_operations.get_cards_due_for_tags(self.selected_tags))
        total_due = len(self.due_cards)
        
        self.stdscr.addstr(start_y, start_x, f"Cards due: {filtered_due_count}/{total_due}", curses.color_pair(4) | curses.A_BOLD)
        
        tag_status = f"Selected tags: {len(self.selected_tags)}/{len(self.tags)}"
        if self.tag_section_active:
            tag_status += " [ACTIVE]"
        self.stdscr.addstr(start_y + 1, start_x, tag_status, curses.color_pair(9))
        
        self.stdscr.addstr(start_y + 2, start_x, "─" * width, curses.color_pair(3))
        
        tags_section_y = start_y + 3
        self.draw_tag_section(tags_section_y, start_x, width)
        
        tag_section_height = min(10, len(self.tags) + 1)
        divider_y = tags_section_y + tag_section_height
        self.stdscr.addstr(divider_y, start_x, "─" * width, curses.color_pair(3))
        
        menu_start_y = divider_y + 1
        self.stdscr.addstr(menu_start_y, start_x, "Menu Options:", curses.color_pair(1) | curses.A_BOLD)
        
        for i, (text, key) in enumerate(self.menu_items):
            item_y = menu_start_y + i + 1
            is_selected = i == self.selected_menu_idx and not self.tag_section_active
            
            style = curses.color_pair(3) | curses.A_BOLD if is_selected else curses.color_pair(2)
            indicator = ">" if is_selected else " "
            
            menu_text = f"{indicator} {text} ({key})"
            self.stdscr.addstr(item_y, start_x, menu_text, style)
    
    def draw_tag_section(self, start_y, start_x, width):
        max_visible_tags = 8
        
        self.stdscr.addstr(start_y, start_x, "Tags:", curses.color_pair(1) | curses.A_BOLD)
        
        if not self.tags:
            self.stdscr.addstr(start_y + 1, start_x, "No tags available.", curses.color_pair(8))
            return
        
        start_idx = max(0, min(self.selected_tag_idx - max_visible_tags // 2, len(self.tags) - max_visible_tags))
        end_idx = min(start_idx + max_visible_tags, len(self.tags))
        
        for i, tag in enumerate(self.tags[start_idx:end_idx], start_idx):
            item_y = start_y + 1 + (i - start_idx)
            is_selected = i == self.selected_tag_idx and self.tag_section_active
            
            style = curses.color_pair(3) | curses.A_BOLD if is_selected else curses.color_pair(2)
            
            tag_display = tag[:width - 15] + ".." if len(tag) > width - 13 else tag
            checkbox = "[✓]" if tag in self.selected_tags else "[ ]"
            indicator = ">" if is_selected else " "
            
            due_count = self.tag_due_counts.get(tag.strip(), 0)
            tag_text = f"{indicator} {checkbox} {tag_display} ({due_count})"
            
            self.stdscr.addstr(item_y, start_x, tag_text, style)
    
    def draw_statistics_section(self, start_y, start_x, width, height):
        self.stdscr.addstr(start_y, start_x, "Statistics", curses.color_pair(1))
        
        terminal_height, terminal_width = self.stdscr.getmaxyx()
        
        for i in range(curses.COLORS):
            if i < 256:
                try:
                    curses.init_pair(i, i, -1)
                except:
                    pass
        
        heatmap_height = 15
        heatmap_width = width
        
        heatmap_drawn = draw_heatmap(self.stdscr, start_y + 1, start_x, heatmap_width, self.review_counts)
        
        if heatmap_drawn:
            calendar_start_y = start_y + heatmap_height + 2
            
            if calendar_start_y + 11 <= terminal_height:
                calendar_width = width // 2 - 2
                
                calendar_drawn = draw_calendar(self.stdscr, calendar_start_y, start_x, self.due_counts)
                
                if calendar_drawn and width >= 80:
                    stats_start_x = start_x + calendar_width + 4
                    draw_statistics(self.stdscr, calendar_start_y, stats_start_x, self.stats)
                elif calendar_drawn and terminal_height - (calendar_start_y + 11) >= 12:
                    stats_start_y = calendar_start_y + 11
                    draw_statistics(self.stdscr, stats_start_y, start_x, self.stats)
    
    def handle_key_input(self, key):
        if key == ord('q'):
            return False
        elif key == ord('a') and not self.tag_section_active:
            add_menu = AddMenu(self.stdscr)
            add_menu.run()
            self.refresh_data()
            return True
        elif key == ord('s'):
            self.draw_message("Search functionality coming soon!", "info")
            return True
        elif key == ord('r'):
            filtered_due_cards = db_operations.get_cards_due_for_tags(self.selected_tags)
            if not filtered_due_cards:
                self.draw_message("No cards due for selected tags!", "info")
                return True
            review_menu = ReviewMenu(self.stdscr, selected_tags=self.selected_tags)
            review_menu.run()
            self.refresh_data()
            return True
        elif key == ord('t'):
            self.tag_section_active = not self.tag_section_active
            self.needs_full_redraw = True
            return True
        
        if self.tag_section_active:
            if key == ord('j') or key == curses.KEY_DOWN:
                self.selected_tag_idx = min(len(self.tags) - 1, self.selected_tag_idx + 1)
            elif key == ord('k') or key == curses.KEY_UP:
                self.selected_tag_idx = max(0, self.selected_tag_idx - 1)
            elif key == ord(' ') or key == ord('\n'):
                if self.tags and 0 <= self.selected_tag_idx < len(self.tags):
                    tag = self.tags[self.selected_tag_idx]
                    if tag in self.selected_tags:
                        self.selected_tags.remove(tag)
                    else:
                        self.selected_tags.add(tag)
            elif key == 27:
                self.tag_section_active = False
        else:
            if key == ord('j') or key == curses.KEY_DOWN:
                self.selected_menu_idx = min(len(self.menu_items) - 1, self.selected_menu_idx + 1)
            elif key == ord('k') or key == curses.KEY_UP:
                self.selected_menu_idx = max(0, self.selected_menu_idx - 1)
            elif key == ord('\n'):
                if self.menu_items[self.selected_menu_idx][1] == 't':
                    self.tag_section_active = True
                    self.needs_full_redraw = True
                else:
                    menu_key = self.menu_items[self.selected_menu_idx][1]
                    return self.handle_key_input(ord(menu_key))
        
        return True
    
    def run(self):
        curses.curs_set(0)
        while True:
            self.update_dimensions()
            self.draw_main_menu()
            self.stdscr.refresh()
            
            key = self.stdscr.getch()
            
            if not self.handle_key_input(key):
                break


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(0)
    
    curses.start_color()
    curses.use_default_colors()
    for i in range(min(curses.COLORS, 256)):
        try:
            curses.init_pair(i, i, -1)
        except:
            pass
    
    ui = MainMenu(stdscr)
    ui.run()


if __name__ == "__main__":
    curses.wrapper(main)
