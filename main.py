#!/usr/bin/env python3
import sys
import argparse
from curses import wrapper
from pathlib import Path
import os

# Import from our modules
from main_menu import MainMenu
from review_menu import ReviewMenu
from config import db_path
from db_operations import create_db


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="Excalibur - A spaced repetition flashcard system")
    
    parser.add_argument("--init", action="store_true", help="Initialize the database and directory structure")
    parser.add_argument("--review", action="store_true", help="Start in review mode directly")
    
    return parser.parse_args(args)


def ensure_initialized():
    """Check if the application has been initialized and initialize if needed."""
    if not os.path.exists(Path(db_path).expanduser()):
        print("Initializing Excalibur...")
        os.makedirs(Path(db_path).expanduser())
        
    if not os.path.exists(Path(db_path + "/cards").expanduser()):
        os.makedirs(Path(db_path + "/cards").expanduser())
        
    if not os.path.exists(Path(db_path + "/scripts").expanduser()):
        os.makedirs(Path(db_path + "/scripts").expanduser())
        
    create_db()


def main(args=None):
    parsed_args = parse_args(args)
    
    # Initialize if requested or if not already initialized
    if parsed_args.init or not os.path.exists(Path(db_path + "/excalibur.db").expanduser()):
        ensure_initialized()
    
    # Start the UI with curses wrapper
    def start_ui(stdscr):
        # If --review flag is set, go directly to review mode
        if parsed_args.review:
            ui = ReviewMenu(stdscr)
            ui.run()
        else:
            # Otherwise, start with the main menu
            ui = MainMenu(stdscr)
            ui.run()
    
    wrapper(start_ui)
    return 0


if __name__ == "__main__":
    sys.exit(main())

