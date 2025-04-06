import curses
from typing import List, Set

from base_ui import BaseUI
from config import symbols
from db_operations import get_tags, new_tag


class ManageTagsMenu(BaseUI):

    def __init__(self, stdscr, selected_tags=None):
        super().__init__(stdscr)
        self.tags = get_tags()
        self.selected_idx = 0
        
        if selected_tags is None:
            self.selected_tags = set()
        elif isinstance(selected_tags, str):
            self.selected_tags = set(tag.strip() for tag in selected_tags.split(',') if tag.strip())
        else:
            self.selected_tags = set(selected_tags)
        
    def draw_tags_menu(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Create box for tags menu
        box_height = min(20, height - 4)
        box_width = min(60, width - 4)
        start_y = (height - box_height) // 2
        start_x = (width - box_width) // 2
        
        # Draw border with title
        self.draw_border(start_y, start_x, box_height, box_width, "Manage Tags")
        
        # Draw list of tags
        content_y = start_y + 2
        content_x = start_x + 3
        
        # Refresh tag list
        self.tags = get_tags()
        
        # Handle case where there are no tags
        if not self.tags:
            message = "No tags created yet. Press 'a' to add a new tag."
            msg_x = start_x + (box_width - len(message)) // 2
            self.stdscr.addstr(content_y + 2, msg_x, message, curses.color_pair(8))
        else:
            max_visible = box_height - 4  # Subtract borders and header/footer
            start_idx = max(0, min(self.selected_idx - max_visible // 2, len(self.tags) - max_visible))
            end_idx = min(start_idx + max_visible, len(self.tags))
            
            # Display tags in the visible range
            for i, tag in enumerate(self.tags[start_idx:end_idx], start_idx):
                # Determine display style
                if i == self.selected_idx:
                    style = curses.color_pair(3) | curses.A_BOLD  # Selected item
                else:
                    style = curses.color_pair(2)  # Normal item
                
                checkbox = "[✓]" if tag in self.selected_tags else "[ ]"
                
                self.stdscr.addstr(content_y + i - start_idx, content_x, f"{checkbox} {tag}", style)
        
        # Instructions at bottom
        instructions = "a: Add new tag | Space: Select/Deselect | j/k: Navigate | q: Back"
        instr_x = start_x + (box_width - len(instructions)) // 2
        self.stdscr.addstr(start_y + box_height - 2, instr_x, instructions, curses.color_pair(8))
        
        self.status_bar.clear()
    
    def run(self):
        while True:
            self.update_dimensions()
            
            self.draw_tags_menu()
            
            key = self.stdscr.getch()
            
            if key == ord('q'):
                break
            elif key == ord('a'):
                # Add new tag
                new_tag_name = self.get_user_input("Enter new tag name:")
                if new_tag_name.strip():
                    new_tag(new_tag_name.strip())
                    self.draw_message(f"Tag '{new_tag_name}' added successfully!", "success")
            # Vim-style navigation keys
            elif key == ord('k') or key == curses.KEY_UP:
                if self.tags:
                    self.selected_idx = max(0, self.selected_idx - 1)
            elif key == ord('j') or key == curses.KEY_DOWN:
                if self.tags:
                    self.selected_idx = min(len(self.tags) - 1, self.selected_idx + 1)
            elif key == ord(' '):
                if self.tags and 0 <= self.selected_idx < len(self.tags):
                    tag = self.tags[self.selected_idx]
                    if tag in self.selected_tags:
                        self.selected_tags.remove(tag)
                    else:
                        self.selected_tags.add(tag)
        
        return self.selected_tags


def main(stdscr):
    ui = ManageTagsMenu(stdscr)
    selected_tags = ui.run()
    
    stdscr.clear()
    stdscr.addstr(2, 2, f"Selected tags: {selected_tags}")
    stdscr.refresh()
    stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(main)
