# Excalibur
Excalibur is a TUI spaced repetition flash card application based on FSRS

## Features
- Flashcards are stored as a markdown file, and can be edited with any text editor.
- Supports tags instead of decks, allowing for a flexible organization of flashcards with multiple tags per card.
- Images are supported, and can be added to flashcards using the `![]()` syntax.
- Pretty markdown rendering with syntax highlighting and other things.
- Spaced repetition based on the Free Spaced Repetition Scheduler (FSRS) algorithm.
- Terminal-based user interface

## Installation
### Dependencies
- Python 3.6+
- Required Python packages:
  - curses 
  - pygments (for syntax highlighting)
  - fsrs
  - term_image (optional, for image display in terminal)

### Installation Steps
1. Clone the repository:
   ```
   git clone https://github.com/Illyarb/Excalibur
   cd excalibur
   ```

2. Install required packages:
   ```
   pip install fsrs pygments
   pip install term_image  # Optional, for image support
   ```

3. Initialize the application:
   ```
   python main.py --init
   ```

## Usage
Run the application with:
```
python main.py
```

To directly start in review mode:
```
python main.py --review
```

### Key Bindings
#### Main Menu
- `a` - Add a new flashcard
- `r` - Review due cards
- `s` - Search cards
- `x` - View statistics
- `t` - Toggle tag selection menu
- `q` - Quit

#### Tag Selection
- `j` / Down Arrow - Move selection down
- `k` / Up Arrow - Move selection up
- Space - Toggle tag selection
- `a` - Select all tags
- `n` - Deselect all tags

#### Review Mode
- `Space` / `h` / Right Arrow - Show answer (when viewing question)
- `Space` - Toggle back to question (when viewing answer)
- You can rate the card based on your retention quality:
* `l` - Rate card as "Again" 
* `k` - Rate card as "Hard"
* `j` - Rate card as "Good"
* `h` - Rate card as "Easy"
* `q` - Quit review session

## File Structure
- `main.py` - Entry point of the application
- `main_menu.py` - Main menu interface
- `review.py` - Card review interface
- `card_operations.py` - Functions for card management
- `db_operations.py` - Database operations
- `renderer.py` - Custom markdown renderer
- `config.py` - Application configuration
- `utils.py` - Utility functions

## Card Format
Cards are stored as markdown files in the excalibur directory, where you can also find the database file for meta data. Each card is represented by two markdown files:
- Front of card: `[card_id]_front.md`
- Back of card: `[card_id]_back.md`

You can use standard markdown syntax for formatting. Pretty much everything is supported, including images, which you can add using the `![]()` syntax.

## Directory Structure
Excalibur creates the following directories:
- `~/.excalibur/` - Main application directory
- `~/.excalibur/cards/` - Stores all flashcard markdown files
- `~/.excalibur/scripts/` - For custom scripts and extensions
- `~/.excalibur/excalibur.db` - SQLite database for card scheduling information

## Contributing
Contributions are welcome! Please feel free to submit issues or pull requests.

### To do:
- Statistics on the front page with cool graphics
- Searching for cards
- Better card editing interface that actually works
- Make it compatible with Anki
- FSRS optimization

## License
MIT License

## Acknowledgments
- This project uses the [FSRS algorithm](https://github.com/open-spaced-repetition/fsrs-rs) which is constantly updating. 
- Inspired by spaced repetition systems like Anki and SuperMemo
