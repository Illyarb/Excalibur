import curses
import os
import subprocess
from pathlib import Path
import uuid
from typing import Set

# Import from our modules
from base_ui import BaseUI
from config import db_path, editor, symbols
from db_operations import add_card, get_tags
from manage_tags_menu import ManageTagsMenu


class AddMenu(BaseUI):
    def __init__(self, stdscr):
        super().__init__(stdscr)
        # Initialize instance variables
        self.selected_tags: Set[str] = set()
    
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
    
    def run(self):
        """Main loop for the add menu"""
        while True:
            # Update dimensions in case terminal was resized
            self.update_dimensions()
            
            # Draw the add menu
            self.draw_add_menu()
            
            # Get user input
            key = self.stdscr.getch()
            
            if key == ord('a'):
                self.create_card()  # Create a new card with current selected tags
                self.stdscr.clear()  # Clear screen after returning from card creation
            elif key == ord('t'):
                # Go to tag management screen
                tags_menu = ManageTagsMenu(self.stdscr, self.selected_tags)
                self.selected_tags = tags_menu.run()
                self.stdscr.clear()  # Clear screen after returning from tag management
            elif key == ord('q'):
                break  # Return to main menu


def main(stdscr):
    """Initialize and run the add menu directly (for testing)"""
    ui = AddMenu(stdscr)
    ui.run()


if __name__ == "__main__":
    curses.wrapper(main)
