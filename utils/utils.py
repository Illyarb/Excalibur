import os
import sys
import tty
import termios
import datetime
from datetime import timedelta

def format_time_diff(time_diff):
    """
    Format a time difference in a user-friendly way.
    
    Args:
        time_diff: A timedelta object representing a time difference
        
    Returns:
        str: A formatted string (e.g., "5min", "2h", "3d", "1w")
    """
    minutes = time_diff.total_seconds() / 60
    hours = minutes / 60
    days = hours / 24
    weeks = days / 7
    
    if minutes < 60:
        return f"{int(minutes)}min"
    elif hours < 24:
        return f"{int(hours)}h"
    elif days < 7:
        return f"{int(days)}d"
    else:
        return f"{int(weeks)}w"

def get_terminal_size():
    """
    Get current terminal size.
    
    Returns:
        tuple: (width, height) of terminal
    """
    return os.get_terminal_size()

def get_keypress():
    """
    Get a single keypress from the terminal.
    Handles special keys like arrow keys.
    
    Returns:
        str: The key pressed, or a special key name (e.g., 'KEY_UP')
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        
        # Handle arrow keys which send escape sequences
        if ch == '\x1b':
            ch += sys.stdin.read(2)
            
            # Map escape sequences to arrow key names
            if ch == '\x1b[A':
                return 'KEY_UP'
            elif ch == '\x1b[B':
                return 'KEY_DOWN'
            elif ch == '\x1b[C':
                return 'KEY_RIGHT'
            elif ch == '\x1b[D':
                return 'KEY_LEFT'
        
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')

def move_cursor(row, col):
    """
    Move the cursor to a specific position in the terminal.
    
    Args:
        row (int): Row number (1-based)
        col (int): Column number (1-based)
    """
    print(f"\033[{row};{col}H", end="")

def print_colored_text(text, color_code):
    """
    Print text with ANSI color code.
    
    Args:
        text (str): Text to print
        color_code (str): ANSI color code (e.g., "31" for red)
    """
    print(f"\033[{color_code}m{text}\033[0m", end="")

def center_text(text, width=None):
    """
    Center text in the terminal or given width.
    
    Args:
        text (str): Text to center
        width (int, optional): Width to center in. Defaults to terminal width.
    
    Returns:
        str: The centered text with appropriate padding
    """
    if width is None:
        width, _ = get_terminal_size()
    
    padding = max(0, (width - len(text)) // 2)
    return " " * padding + text

def format_date(dt):
    """
    Format a datetime object in a readable format.
    
    Args:
        dt (datetime): The datetime to format
        
    Returns:
        str: Formatted date string
    """
    if dt is None:
        return "N/A"
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # If date is today
    if dt.date() == now.date():
        return f"Today at {dt.strftime('%H:%M')}"
    
    # If date is yesterday
    if dt.date() == (now - timedelta(days=1)).date():
        return f"Yesterday at {dt.strftime('%H:%M')}"
    
    # If date is within a week
    if (now - dt).days < 7:
        return dt.strftime('%A at %H:%M')  # Day of week
    
    # Otherwise full date
    return dt.strftime('%Y-%m-%d %H:%M')

def get_days_until(date):
    """
    Calculate days until a given date.
    
    Args:
        date (datetime): The target date
        
    Returns:
        int: Number of days until the date
    """
    if date is None:
        return None
    
    now = datetime.datetime.now(datetime.timezone.utc)
    difference = date - now
    return max(0, difference.days)

def truncate_text(text, max_length, suffix="..."):
    """
    Truncate text to a maximum length.
    
    Args:
        text (str): The text to truncate
        max_length (int): Maximum length
        suffix (str, optional): Suffix to add when truncated. Defaults to "...".
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length-len(suffix)] + suffix
