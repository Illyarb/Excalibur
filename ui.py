import curses
from typing import List, Set, Dict
import os
from pathlib import Path

# Import from our modules
from config import db_path
from main_menu import MainMenu

def main(stdscr):
    """
    Main entry point for the Excalibur UI.
    Initializes the main menu and starts the application.
    
    Args:
        stdscr: The curses window object
    """
    # Create the main menu and run it
    ui = MainMenu(stdscr)
    ui.run()

if __name__ == "__main__":
    # Use the curses wrapper to initialize and run the application
    curses.wrapper(main)
