import curses
from typing import Dict, List

# Import from our modules
from base_ui import BaseUI
from config import symbols
from db_operations import get_cards_due
from review_menu import ReviewMenu
from add_menu import AddMenu


class MainMenu(BaseUI):
    def __init__(self, stdscr):
        super().__init__(stdscr)
        # Initialize instance variables
        self.due_cards = get_cards_due()
    
    def draw_main_menu(self):
        """Draw the main menu interface"""
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
        """Main loop for the main menu"""
        while True:
            # Update dimensions in case terminal was resized
            self.update_dimensions()
            
            # Draw the main menu
            self.draw_main_menu()
            
            # Get user input
            key = self.stdscr.getch()
            
            if key == ord('q'):
                break
            elif key == ord('a'):
                # Go to Add Menu
                add_menu = AddMenu(self.stdscr)
                add_menu.run()
                self.stdscr.clear()  # Clear screen after returning
            elif key == ord('r'):
                # Go to Review Menu
                review_menu = ReviewMenu(self.stdscr)
                review_menu.run()
                self.stdscr.clear()  # Clear screen after returning
            elif key == ord('s'):
                # Search cards (placeholder)
                self.draw_message("Search functionality coming soon!", "info")
            elif key == ord('x'):
                # Statistics (placeholder)
                self.draw_message("Statistics functionality coming soon!", "info")


def main(stdscr):
    """Initialize and run the main menu"""
    ui = MainMenu(stdscr)
    ui.run()


if __name__ == "__main__":
    curses.wrapper(main)
