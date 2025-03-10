global db_path 
global editor
db_path = "~/.local/share/excalibur"
editor = "nvim"

# Dracula color scheme
colors = {
    "background": 0,        # Background
    "foreground": 15,       # Foreground (white)
    "current_line": 234,    # Current line (darker gray)
    "selection": 236,       # Selection (gray)
    "comment": 61,          # Comment (bluish)
    "cyan": 117,            # Cyan
    "green": 84,            # Green
    "orange": 215,          # Orange
    "pink": 212,            # Pink
    "purple": 141,          # Purple
    "red": 203,             # Red
    "yellow": 228,          # Yellow
}

# UI element colors
ui_colors = {
    "title": colors["purple"],              # Title text
    "menu_item": colors["foreground"],      # Normal menu items
    "selected_item": colors["cyan"],        # Selected menu item
    "highlight": colors["green"],           # Highlighted elements
    "warning": colors["orange"],            # Warning messages
    "error": colors["red"],                 # Error messages
    "success": colors["green"],             # Success messages
    "info": colors["comment"],              # Info messages
    "tag": colors["yellow"],                # Tags
    "selected_tag": colors["pink"],         # Selected tags
    "border": colors["selection"],          # Borders
    "status_bar": colors["current_line"],   # Status bar background
    "status_text": colors["foreground"],    # Status bar text
}

# UI symbols
symbols = {
    "checkbox_empty": "□",
    "checkbox_checked": "■",
    "bullet": "•",
    "arrow": "→",
    "star": "★",
    "tag": "⚑",
    "card": "󰓥",
    "add": "+",
    "search": "🔍",
    "stats": "📊",
    "review": "📚",
    "settings": "⚙️",
}

