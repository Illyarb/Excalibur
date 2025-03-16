import curses
import os
import subprocess
from pathlib import Path
import uuid

# Import from our modules
from config import db_path, editor, ui_colors, symbols, colors
from db_operations import get_cards_due

class BaseUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        
        # Setup curses
        curses.curs_set(0)  # Disable cursor
        curses.use_default_colors()
        self.init_colors()
        
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

    def draw_border(self, y, x, height, width, title=""):
        """Draw a bordered box with optional title"""
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
    
    def update_dimensions(self):
        """Update terminal dimensions and status bar position"""
        self.height, self.width = self.stdscr.getmaxyx()
        self.status_bar.resize(1, self.width)
        self.status_bar.mvwin(self.height-1, 0)
        
    def run(self):
        """Run method to be implemented by derived classes"""
        raise NotImplementedError("Subclasses must implement the run method")
