import curses
from typing import List, Set, Dict
import os
from pathlib import Path

from config import db_path
from main_menu import MainMenu

def main(stdscr):
    ui = MainMenu(stdscr)
    ui.run()

if __name__ == "__main__":
    curses.wrapper(main)
