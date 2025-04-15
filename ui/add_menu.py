import curses
import os
import subprocess
from pathlib import Path
import uuid
from typing import Set

from ui.base_ui import BaseUI
from config import db_path, editor, symbols
from operations.db_operations import add_card, get_tags
from ui.manage_tags_menu import ManageTagsMenu


class AddMenu(BaseUI):
    def __init__(self, stdscr):
        super().__init__(stdscr)
        self.selected_tags: Set[str] = set()
    
    def create_card(self):
        """Create a new flashcard with selected tags"""
        if not self.selected_tags:
            self.draw_message("Please select at least one tag first", "warning")
            return
            
        card_id = str(uuid.uuid4())
        scripts_dir = Path(db_path + "/cards").expanduser()
        
        # Save current terminal state
        curses.def_prog_mode()
        curses.endwin()
        
        front_path = scripts_dir / f"{card_id}_front.md"
        subprocess.run([editor, str(front_path)])
        
        # Restore terminal state
        curses.reset_prog_mode()
        self.stdscr.refresh()
        
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
    
    def draw_add_menu(self):
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
        
        self.stdscr.addstr(content_y, content_x, f"{symbols['card']} a", curses.color_pair(3))
        self.stdscr.addstr(content_y, content_x + 4, "- Create new card", curses.color_pair(2))
        self.stdscr.addstr(content_y + 1, content_x, f"{symbols['tag']} t", curses.color_pair(3))
        self.stdscr.addstr(content_y + 1, content_x + 4, "- Manage tags", curses.color_pair(2))
        self.stdscr.addstr(content_y + 2, content_x, f"{symbols['arrow']} q", curses.color_pair(3))
        self.stdscr.addstr(content_y + 2, content_x + 4, "- Return to main menu", curses.color_pair(2))
        self.stdscr.addstr(content_y + 4, start_x + 1, "─" * (box_width - 2), curses.color_pair(3))
        
        # Display currently selected tags
        self.stdscr.addstr(content_y + 5, content_x, "Selected Tags:", curses.color_pair(1) | curses.A_BOLD)
        if self.selected_tags:
            # Display tags with proper formatting
            max_tag_width = box_width - 8
            
            # Display tags one per line
            for i, tag in enumerate(self.selected_tags):
                if i < 4:  # Limit visible tags to avoid overflow
                    tag_display = f"• {tag}"
                    self.stdscr.addstr(content_y + 6 + i, content_x, tag_display, curses.color_pair(10))
                elif i == 4:
                    remaining = len(self.selected_tags) - 4
                    self.stdscr.addstr(content_y + 6 + i, content_x, 
                                      f"(+{remaining} more...)", curses.color_pair(8))
                    break
        else:
            self.stdscr.addstr(content_y + 6, content_x, "None", curses.color_pair(8))
    
    def run(self):
        """Main loop for the add menu"""
        while True:
            self.update_dimensions()
            
            self.draw_add_menu()
            
            # Get user input
            key = self.stdscr.getch()
            
            if key == ord('a'):
                self.create_card()  
                self.stdscr.clear()  
            elif key == ord('t'):
                # Go to tag management screen
                tags_menu = ManageTagsMenu(self.stdscr, self.selected_tags)
                selected_tags = tags_menu.run()
                
                # Convert returned tags to a set
                if isinstance(selected_tags, str):
                    self.selected_tags = set(tag.strip() for tag in selected_tags.split(',') if tag.strip())
                elif isinstance(selected_tags, set):
                    self.selected_tags = selected_tags
                
                self.stdscr.clear()  # Clear screen after returning from tag management
            elif key == ord('q'):
                break  # Return to main menu


def main(stdscr):
    ui = AddMenu(stdscr)
    ui.run()


if __name__ == "__main__":
    curses.wrapper(main)

