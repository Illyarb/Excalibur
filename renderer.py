from parser import ElementType, MarkdownElement, MarkdownParser, Table, TableCell
from typing import List, Union, Optional
import re
import shutil
import textwrap
import pygments
from pygments.lexers import get_lexer_by_name
from pygments.formatters import Terminal256Formatter
from pygments.util import ClassNotFound
import random
import os
import subprocess
import base64
from io import BytesIO

try:
    from term_image.image import from_file, from_url, AutoImage
    from term_image.image import Size as ImageSize
    from term_image.image import Size
    TERM_IMAGE_AVAILABLE = True
except ImportError:
    TERM_IMAGE_AVAILABLE = False

class ColorConfig:
    def __init__(self, colored_output=True):
        if colored_output:
            # Generate random colors for headings
            h1_color = (random.randint(160, 255), random.randint(160, 255), random.randint(160, 255))
            h2_color = (random.randint(160, 255), random.randint(160, 255), random.randint(160, 255))
            h3_color = (random.randint(160, 255), random.randint(160, 255), random.randint(160, 255))
            h4_color = (random.randint(160, 255), random.randint(160, 255), random.randint(160, 255))
            
            # Convert RGB to ANSI escape sequences
            self.H1_COLOR = f"\033[38;2;{h1_color[0]};{h1_color[1]};{h1_color[2]}m"
            self.H2_COLOR = f"\033[38;2;{h2_color[0]};{h2_color[1]};{h2_color[2]}m"
            self.H3_COLOR = f"\033[38;2;{h3_color[0]};{h3_color[1]};{h3_color[2]}m"
            self.H4_COLOR = f"\033[38;2;{h4_color[0]};{h4_color[1]};{h4_color[2]}m"
            
            self.BOLD, self.ITALIC, self.UNDERLINE, self.DIM, self.RESET = "\033[1m", "\033[3m", "\033[4m", "\033[2m", "\033[0m"
            self.BLACK, self.RED, self.GREEN, self.YELLOW, self.BLUE, self.MAGENTA, self.CYAN, self.WHITE = "\033[30m", "\033[31m", "\033[32m", "\033[33m", "\033[34m", "\033[35m", "\033[36m", "\033[37m"
            self.BG_WHITE = "\033[47m"
            self.BRIGHT_BLACK, self.BRIGHT_RED, self.BRIGHT_GREEN, self.BRIGHT_YELLOW = "\033[90m", "\033[91m", "\033[92m", "\033[93m"
            self.BRIGHT_BLUE, self.BRIGHT_MAGENTA, self.BRIGHT_CYAN, self.BRIGHT_WHITE = "\033[94m", "\033[95m", "\033[96m", "\033[97m"
            
            # Use random colors for headings
            self.HEADING1_TEXT = self.BOLD + self.H1_COLOR
            self.HEADING1_BOX = self.H1_COLOR
            self.HEADING1_CONTENT = self.BOLD + self.H1_COLOR
            self.HEADING2_TEXT = self.BOLD + self.H2_COLOR
            self.HEADING2_DECORATION = self.H2_COLOR
            self.HEADING3_TEXT = self.BOLD + self.H3_COLOR
            self.HEADING3_DECORATION = self.H3_COLOR
            
            # Existing color assignments
            self.BOLD_TEXT = self.BOLD + self.BRIGHT_WHITE
            self.ITALIC_TEXT = self.ITALIC + self.BRIGHT_CYAN
            self.CODE_TEXT = self.BLACK + self.BG_WHITE
            self.LINK_TEXT = self.UNDERLINE + self.BRIGHT_BLUE
            self.LINK_URL = self.DIM + self.BRIGHT_BLACK
            self.BLOCKQUOTE_TEXT = self.DIM + self.BRIGHT_GREEN
            self.BLOCKQUOTE_BORDER = self.GREEN
            self.HR_COLOR = self.BRIGHT_MAGENTA
            self.LIST_BULLET_DASH = self.BRIGHT_GREEN
            self.LIST_BULLET_ASTERISK = self.BRIGHT_YELLOW
            self.LIST_BULLET_PLUS = self.BRIGHT_MAGENTA
            self.LIST_NUMBER = self.BRIGHT_CYAN
            self.CODE_BLOCK_BORDER = self.BRIGHT_BLUE
            self.CODE_BLOCK_LANGUAGE = self.BOLD + self.BRIGHT_WHITE
            self.CODE_BLOCK_TEXT = self.WHITE
            self.CODE_BLOCK_LINE_NUM = "\033[38;5;60m"
            self.CODE_BLOCK_ICON = "  "
            self.IMAGE_CAPTION = self.ITALIC + self.BRIGHT_MAGENTA
            self.IMAGE_PATH = self.DIM + self.BRIGHT_BLACK
            
            self.COMMENT_TEXT = self.DIM + self.BRIGHT_BLACK
            self.TABLE_BORDER = self.BRIGHT_BLUE
            self.TABLE_HEADER_BG = "\033[48;5;27m"  # Brighter blue background
            self.TABLE_HEADER_TEXT = self.BOLD + self.BRIGHT_WHITE
            self.TABLE_ROW_ODD = "\033[48;5;234m"
            self.TABLE_ROW_EVEN = "\033[48;5;236m"
            self.TABLE_TEXT = self.WHITE
        else:
            self.BOLD = self.ITALIC = self.UNDERLINE = self.DIM = self.RESET = ""
            self.BLACK = self.RED = self.GREEN = self.YELLOW = self.BLUE = self.MAGENTA = self.CYAN = self.WHITE = ""
            self.BG_WHITE = ""
            self.BRIGHT_BLACK = self.BRIGHT_RED = self.BRIGHT_GREEN = self.BRIGHT_YELLOW = ""
            self.BRIGHT_BLUE = self.BRIGHT_MAGENTA = self.BRIGHT_CYAN = self.BRIGHT_WHITE = ""
            
            self.H1_COLOR = self.H2_COLOR = self.H3_COLOR = self.H4_COLOR = ""
            self.HEADING1_TEXT = self.HEADING1_BOX = self.HEADING1_CONTENT = ""
            self.HEADING2_TEXT = self.HEADING2_DECORATION = ""
            self.HEADING3_TEXT = self.HEADING3_DECORATION = ""
            self.BOLD_TEXT = self.ITALIC_TEXT = self.CODE_TEXT = self.LINK_TEXT = self.LINK_URL = self.BLOCKQUOTE_TEXT = self.BLOCKQUOTE_BORDER = ""
            self.HR_COLOR = ""
            self.LIST_BULLET_DASH = self.LIST_BULLET_ASTERISK = self.LIST_BULLET_PLUS = self.LIST_NUMBER = ""
            self.CODE_BLOCK_BORDER = self.CODE_BLOCK_LANGUAGE = self.CODE_BLOCK_TEXT = self.CODE_BLOCK_LINE_NUM = ""
            self.CODE_BLOCK_ICON = ""
            self.IMAGE_CAPTION = self.IMAGE_PATH = ""
            self.COMMENT_TEXT = ""
            self.TABLE_BORDER = self.TABLE_HEADER_BG = self.TABLE_HEADER_TEXT = ""
            self.TABLE_ROW_ODD = self.TABLE_ROW_EVEN = self.TABLE_TEXT = ""

class BoxDrawing:
    def __init__(self, colors: ColorConfig):
        self.colors = colors
        try:
            self.terminal_width = shutil.get_terminal_size()[0]
        except (AttributeError, ValueError, OSError):
            self.terminal_width = 80
            
        self.language_icons = {
            "python": "\ue73c",
            "javascript": "\ue781",
            "js": "\ue781",
            "typescript": "\ue628",
            "ts": "\ue628",
            "html": "\ue736",
            "css": "\ue749",
            "java": "\ue738",
            "c": "\ue61e",
            "cpp": "\ue61d",
            "c++": "\ue61d",
            "csharp": "\ue77a",
            "c#": "\ue77a",
            "go": "\ue724",
            "ruby": "\ue791",
            "rust": "\ue7a8",
            "php": "\ue73d",
            "swift": "\ue755",
            "kotlin": "\ue634",
            "scala": "\ue737",
            "shell": "\ue795",
            "bash": "\ue795",
            "sh": "\ue795",
            "powershell": "\ue7ad",
            "ps1": "\ue7ad",
            "sql": "\ue706",
            "markdown": "\ue73e",
            "md": "\ue73e",
            "json": "\ue60b",
            "yaml": "\ue73b",
            "yml": "\ue73b",
            "xml": "\ue619",
            "r": "\ue7b2",
            "dockerfile": "\ue7b0",
            "docker": "\ue7b0",
            "lua": "\ue620",
            "perl": "\ue769",
            "haskell": "\ue777",
            "hs": "\ue777",
        }
        
        self.numbered_bullets = ["➊", "➋", "➌", "➍", "➎", "➏", "➐", "➑", "➒", "➓"]
    
    def fancy_box(self, text: str) -> str:
        max_width = self.terminal_width - 10
        wrapped_lines = textwrap.wrap(text, width=max_width)
        content_width = max(len(line) for line in wrapped_lines)
        box_width = content_width + 4
        center_offset = max(0, (self.terminal_width - box_width) // 2)
        padding_str = " " * center_offset
        c = self.colors
        
        result = []
        result.append(f"{padding_str}{c.HEADING1_BOX}┏{'━' * box_width}┓{c.RESET}")
        
        for line in wrapped_lines:
            padding_left = (box_width - len(line)) // 2
            padding_right = box_width - len(line) - padding_left
            result.append(f"{padding_str}{c.HEADING1_BOX}┃{' ' * padding_left}{c.HEADING1_CONTENT}{line}{c.HEADING1_BOX}{' ' * padding_right}┃{c.RESET}")
        
        result.append(f"{padding_str}{c.HEADING1_BOX}┗{'━' * box_width}┛{c.RESET}")
        
        return "\n".join(result)
    
    def h2_decoration(self, text: str) -> str:
        c = self.colors
        line = "═" * (len(text) + 4)
        center_offset = max(0, (self.terminal_width - len(text)) // 2)
        padding_str = " " * center_offset
        underline_padding = " " * max(0, center_offset - 2)
        return f"{padding_str}{c.HEADING2_TEXT}{text}{c.RESET}\n{underline_padding}{c.HEADING2_DECORATION}{line}{c.RESET}"
    
    def h3_decoration(self, text: str) -> str:
        c = self.colors
        text_width = len(text)
        center_offset = max(0, (self.terminal_width - text_width - 6) // 2)
        padding_str = " " * center_offset
        
        return f"{padding_str}{c.HEADING3_DECORATION}✧✧ {c.HEADING3_TEXT}{text}{c.HEADING3_DECORATION} ✧✧{c.RESET}"
    
    def h4_decoration(self, text: str, level=1) -> str:
        c = self.colors
        prefix = '#' * level + ' '
        h4_color = c.H4_COLOR + c.BOLD
        margin = 4
        margin_str = " " * margin
        
        return f"{margin_str}{h4_color}→ {text}{c.RESET}"
    
    def code_block_box(self, content: str, language: Optional[str] = None) -> str:
        c = self.colors
        
        if language and c.RESET:
            try:
                lexer = get_lexer_by_name(language, stripall=True)
                formatter = Terminal256Formatter(style='monokai')
                highlighted_content = pygments.highlight(content, lexer, formatter)
                if highlighted_content.endswith('\n'):
                    highlighted_content = highlighted_content[:-1]
                lines = highlighted_content.split('\n')
            except (ClassNotFound, ImportError):
                lines = content.split('\n')
        else:
            lines = content.split('\n')
        
        max_line_length = max(len(re.sub(r'\x1b\[[0-9;]*m', '', line)) for line in lines)
        result = []
        
        bg_color = "\033[48;5;235m"
        
        if language:
            lang_lower = language.lower()
            icon = self.language_icons.get(lang_lower, "")
            result.append(f"{c.CODE_BLOCK_LANGUAGE}{icon} {language} {c.RESET}")
        
        indent = "    "
        result.append(f"{indent}{c.CODE_BLOCK_BORDER}╶{'─' * (max_line_length + 8)}╴{c.RESET}")
        
        for i, line in enumerate(lines, 1):
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
            padding_right = max(0, max_line_length - len(clean_line))
            
            line_num = f"{bg_color}{c.CODE_BLOCK_LINE_NUM}{i:2d}{' '} {c.CODE_BLOCK_LINE_NUM}│ "
            
            if c.RESET and any(esc in line for esc in ['\x1b[']):
                colored_line = line.replace(c.RESET, c.RESET + bg_color)
                result.append(f"{indent}{line_num}{colored_line}{bg_color}{' ' * padding_right}  {c.RESET}")
            else:
                result.append(f"{indent}{line_num}{c.CODE_BLOCK_TEXT}{line}{' ' * padding_right}  {c.RESET}")
        
        result.append(f"{indent}{c.CODE_BLOCK_BORDER}╶{'─' * (max_line_length + 8)}╴{c.RESET}")
        
        return "\n".join(result)
    
    def blockquote_decoration(self, content: str) -> str:
        c = self.colors
        lines = content.split('\n')
        result = []
        
        for i in range(len(lines)):
            lines[i] = lines[i].replace("\"", "\"")
            
        if lines and not lines[0].startswith("\""):
            lines[0] = "\"" + lines[0]
        if lines and not lines[-1].endswith("\""):
            lines[-1] = lines[-1] + "\""
        
        result.append(f"{c.BLOCKQUOTE_BORDER}╭─╴{c.RESET}")
        for line in lines:
            result.append(f"{c.BLOCKQUOTE_BORDER}│ {c.BLOCKQUOTE_TEXT}{line}{c.RESET}")
        result.append(f"{c.BLOCKQUOTE_BORDER}╰─╴{c.RESET}")
        
        return "\n".join(result)
    
    def horizontal_rule(self, style: str = "normal") -> str:
        c = self.colors
        width = self.terminal_width - 4
        
        if style == "heavy":
            eq_count = width // 2
            fancy_line = "🟰" * eq_count
            return f"{c.HR_COLOR}{fancy_line}{c.RESET}"
        elif style == "double":
            return f"{c.HR_COLOR}{'═' * width}{c.RESET}"
        else:
            return f"{c.HR_COLOR}{'─' * width}{c.RESET}"
    
    def comment_box(self, content: str) -> str:
        c = self.colors
        lines = content.split('\n')
        result = []
        
        result.append(f"{c.COMMENT_TEXT}<!-- {lines[0]}")
        
        for line in lines[1:]:
            result.append(f"{c.COMMENT_TEXT}     {line}")
            
        result.append(f"{c.COMMENT_TEXT} -->{c.RESET}")
        
        return "\n".join(result)
    
    def table_box(self, table) -> str:
        c = self.colors
        result = []
        
        if not table.headers or not isinstance(table, Table):
            return "[Invalid Table]"
        
        col_count = len(table.headers)
        col_widths = [0] * col_count
        
        for i, header in enumerate(table.headers):
            if i < col_count:
                header_text = self._get_plain_text(header.content)
                col_widths[i] = max(col_widths[i], len(header_text))
        
        for row in table.rows:
            for i, cell in enumerate(row):
                if i < col_count:
                    cell_text = self._get_plain_text(cell.content)
                    col_widths[i] = max(col_widths[i], len(cell_text))
        
        col_widths = [w + 2 for w in col_widths]
        
        # Calculate total table width including borders
        table_width = sum(col_widths) + col_count + 1
        
        # Calculate centering padding
        center_padding = " " * max(0, (self.terminal_width - table_width) // 2)
        
        # Build table with centering - properly formatted borders
        result.append(f"{center_padding}{c.TABLE_BORDER}╭{'─' * col_widths[0]}{'┬'.join(['─' * w for w in col_widths[1:]])}╮{c.RESET}")
        
        # Build header row properly
        header_row = f"{c.TABLE_BORDER}│"
        for i, header in enumerate(table.headers):
            if i < col_count:
                header_content = self._render_inline_content(header.content)
                aligned_content = self._align_text(header_content, col_widths[i], header.alignment)
                header_row += f"{c.TABLE_HEADER_BG}{c.TABLE_HEADER_TEXT}{aligned_content}{c.RESET}{c.TABLE_BORDER}"
                if i < col_count - 1:
                    header_row += "│"
        header_row += f"│{c.RESET}"
        result.append(f"{center_padding}{header_row}")
        
        # Proper separator row
        separator_row = f"{c.TABLE_BORDER}├"
        for i, width in enumerate(col_widths):
            alignment = table.alignments[i] if i < len(table.alignments) else 'left'
            if alignment == 'center':
                separator_row += f"{'─' * ((width - 2) // 2)}:{'─' * ((width - 2) // 2)}"
            elif alignment == 'right':
                separator_row += f"{'─' * (width - 1)}:"
            elif alignment == 'left':
                separator_row += f":{'─' * (width - 1)}"
            else:
                separator_row += '─' * width
                
            if i < col_count - 1:
                separator_row += "┼"
                
        separator_row += f"┤{c.RESET}"
        result.append(f"{center_padding}{separator_row}")
        
        # Build data rows properly
        for row_idx, row in enumerate(table.rows):
            bg_color = c.TABLE_ROW_ODD if row_idx % 2 == 0 else c.TABLE_ROW_EVEN
            data_row = f"{c.TABLE_BORDER}│"
            
            for i, cell in enumerate(row):
                if i < col_count:
                    cell_content = self._render_inline_content(cell.content)
                    aligned_content = self._align_text(cell_content, col_widths[i], cell.alignment)
                    data_row += f"{bg_color}{c.TABLE_TEXT}{aligned_content}{c.RESET}{c.TABLE_BORDER}"
                    if i < col_count - 1:
                        data_row += "│"
            
            data_row += f"│{c.RESET}"
            result.append(f"{center_padding}{data_row}")
            
        # Proper bottom border with rounded corners
        border_bottom = f"{c.TABLE_BORDER}╰"
        for i, width in enumerate(col_widths):
            border_bottom += "─" * width
            if i < col_count - 1:
                border_bottom += "┴"
        border_bottom += f"╯{c.RESET}"
        result.append(f"{center_padding}{border_bottom}")
        
        return "\n".join(result)
    
    def _align_text(self, text, width, alignment):
        text_width = len(re.sub(r'\x1b\[[0-9;]*m', '', text))
        padding = width - text_width
        
        if alignment == 'right':
            return f"{' ' * padding}{text}"
        elif alignment == 'center':
            left_pad = padding // 2
            right_pad = padding - left_pad
            return f"{' ' * left_pad}{text}{' ' * right_pad}"
        else:  # left or default
            return f"{text}{' ' * padding}"
    
    def _get_plain_text(self, content):
        result = ""
        for item in content:
            if isinstance(item, str):
                result += item
            elif isinstance(item, MarkdownElement):
                if hasattr(item, 'content') and isinstance(item.content, list):
                    result += self._get_plain_text(item.content)
                elif isinstance(item.content, str):
                    result += item.content
                    
        return result
    
    def _render_inline_content(self, content):
        result = ""
        c = self.colors
        
        for item in content:
            if isinstance(item, str):
                result += item
            elif isinstance(item, MarkdownElement):
                if item.type == ElementType.BOLD:
                    inner_content = self._get_plain_text(item.content)
                    result += f"{c.BOLD_TEXT}{inner_content}{c.RESET}"
                elif item.type == ElementType.ITALIC:
                    inner_content = self._get_plain_text(item.content)
                    result += f"{c.ITALIC_TEXT}{inner_content}{c.RESET}"
                elif item.type == ElementType.CODE:
                    result += f"{c.CODE_TEXT}{item.content}{c.RESET}"
                elif item.type == ElementType.LINK:
                    link_text = self._get_plain_text(item.content)
                    result += f"{c.LINK_TEXT}{link_text}{c.RESET} {c.LINK_URL}[{item.url}]{c.RESET}"
        
        return result

class TermImageRenderer:
    def __init__(self):
        self.cache = {}
        # Check for kitty terminal protocol support
        self.kitty_support = self._check_kitty_support()
    
    def _check_kitty_support(self):
        """Check if the terminal supports kitty graphics protocol"""
        return os.environ.get('TERM') == 'xterm-kitty' or 'KITTY_WINDOW_ID' in os.environ
    
    def can_render_images(self):
        return TERM_IMAGE_AVAILABLE
    
    def render_image(self, img_path: str, caption: str = None) -> str:
        if not self.can_render_images():
            return f"[Image: {caption or ''}] ({img_path})"
        
        if not os.path.exists(img_path):
            return f"[Image Not Found: {img_path}]"
        
        if img_path not in self.cache:
            try:
                # Let term-image's from_file function automatically detect the best renderer
                self.cache[img_path] = from_file(img_path)
            except Exception as e:
                return f"[Image Error: {str(e)}] ({img_path})"
        
        image = self.cache[img_path]
        
        try:
            # Use the image directly - term-image handles rendering
            # We'll use draw() to get a string representation (draw returns None)
            import io
            import sys
            
            # Capture image output from image.draw()
            old_stdout = sys.stdout
            new_stdout = io.StringIO()
            sys.stdout = new_stdout
            
            image.draw()
            
            # Restore stdout and get captured output
            sys.stdout = old_stdout
            rendered = new_stdout.getvalue()
            
            # Add caption if provided
            if caption:
                c = ColorConfig().IMAGE_CAPTION
                reset = ColorConfig().RESET
                path_color = ColorConfig().IMAGE_PATH
                
                try:
                    terminal_width = shutil.get_terminal_size()[0]
                except (AttributeError, ValueError, OSError):
                    terminal_width = 80
                
                # Calculate visible length (without counting color codes)
                visible_length = len(caption) + len(img_path) + 3  # +3 for " ()" around the path
                
                # Add padding to center the caption
                center_padding = " " * max(0, (terminal_width - visible_length) // 2)
                
                return f"{rendered}\n{center_padding}{c}{caption}{reset} {path_color}({img_path}){reset}"
            else:
                return rendered
            
        except Exception as e:
            # If capturing output failed, try simpler approach
            try:
                return f"{str(image)}\n[{caption or ''} ({img_path})]"
            except:
                return f"[Image Rendering Error: {str(e)}] ({img_path})"

class EnhancedMarkdownRenderer:
    def __init__(self, colored_output=True):
        self.parser = MarkdownParser()
        self.colors = ColorConfig(colored_output)
        self.box_tools = BoxDrawing(self.colors)
        self.terminal_width = self.box_tools.terminal_width
        self.image_renderer = TermImageRenderer()
    
    def render(self, md_text: str) -> str:
        elements = self.parser.parse(md_text)
        rendered_text = ""
        
        for element in elements:
            if element.type == ElementType.HEADING:
                rendered_text += self._render_heading(element)
            elif element.type == ElementType.PARAGRAPH:
                rendered_text += self._render_paragraph(element)
            elif element.type in [ElementType.DASH_RULE, ElementType.ASTERISK_RULE, ElementType.UNDERSCORE_RULE]:
                rendered_text += self._render_horizontal_rule(element)
            elif element.type == ElementType.CODE_BLOCK:
                rendered_text += self._render_code_block(element)
            elif element.type == ElementType.BLOCKQUOTE:
                rendered_text += self._render_blockquote(element)
            elif element.type in [ElementType.DASH_LIST, ElementType.ASTERISK_LIST, ElementType.PLUS_LIST]:
                rendered_text += self._render_unordered_list(element)
            elif element.type == ElementType.ORDERED_LIST:
                rendered_text += self._render_ordered_list(element)
            elif element.type == ElementType.TEXT:
                rendered_text += self._render_text(element)
            elif element.type == ElementType.IMAGE:
                rendered_text += self._render_image(element)
            elif element.type == ElementType.COMMENT:
                rendered_text += self._render_comment(element)
            elif element.type == ElementType.TABLE:
                rendered_text += self._render_table(element)
        
        return rendered_text
    
    def _render_heading(self, element: MarkdownElement) -> str:
        content = self._render_inline_content(element.content)
        level = element.level
        
        if level == 1:
            return f"\n{self.box_tools.fancy_box(content)}\n\n"
        elif level == 2:
            return f"\n{self.box_tools.h2_decoration(content)}\n\n"
        elif level == 3:
            return f"\n{self.box_tools.h3_decoration(content)}\n\n"
        else:
            return f"\n{self.box_tools.h4_decoration(content, level - 3)}\n\n"
    
    def _render_paragraph(self, element: MarkdownElement) -> str:
        content = self._render_inline_content(element.content)
        wrapped_text = textwrap.fill(content, width=self.terminal_width - 4)
        return f"{wrapped_text}\n\n"
    
    def _render_horizontal_rule(self, element: MarkdownElement) -> str:
        style = "normal" if element.type == ElementType.DASH_RULE else ("heavy" if element.type == ElementType.ASTERISK_RULE else "double")
        return f"\n{self.box_tools.horizontal_rule(style)}\n\n"
    
    def _render_code_block(self, element: MarkdownElement) -> str:
        language = getattr(element, 'language', '')
        return f"\n{self.box_tools.code_block_box(element.content, language)}\n\n"
    
    def _render_blockquote(self, element: MarkdownElement) -> str:
        content = self._render_inline_content(element.content)
        return f"\n{self.box_tools.blockquote_decoration(content)}\n\n"
    
    def _render_unordered_list(self, element: MarkdownElement) -> str:
        c = self.colors
        result = "\n"
        
        bullet = {
            ElementType.DASH_LIST: f"{c.LIST_BULLET_DASH}• {c.RESET}",
            ElementType.ASTERISK_LIST: f"{c.LIST_BULLET_ASTERISK}◦ {c.RESET}",
            ElementType.PLUS_LIST: f"{c.LIST_BULLET_PLUS}▪ {c.RESET}"
        }[element.type]
        
        for item in element.content:
            item_content = self._render_inline_content(item)
            wrapped_content = textwrap.fill(
                item_content, 
                width=self.terminal_width - 10,
                initial_indent="    " + bullet,
                subsequent_indent="        "
            )
            result += f"{wrapped_content}\n"
        
        return f"{result}\n"
    
    def _render_ordered_list(self, element: MarkdownElement) -> str:
        c = self.colors
        result = "\n"
        
        for i, item in enumerate(element.content, 1):
            item_content = self._render_inline_content(item)
            bullet_idx = (i - 1) % 10
            num_str = f"{c.LIST_NUMBER}{self.box_tools.numbered_bullets[bullet_idx]} {c.RESET}"
            
            wrapped_content = textwrap.fill(
                item_content, 
                width=self.terminal_width - 10,
                initial_indent="    " + num_str,
                subsequent_indent="        "
            )
            result += f"{wrapped_content}\n"
        
        return f"{result}\n"
    
    def _render_text(self, element: MarkdownElement) -> str:
        return f"{element.content[0]}\n\n"
    
    def _render_image(self, element: MarkdownElement) -> str:
        alt_text = self._render_inline_content(element.content) if element.content else ""
        image_path = element.url if element.url else ""
        
        return f"\n{self.image_renderer.render_image(image_path, alt_text)}\n\n"
    
    def _render_comment(self, element: MarkdownElement) -> str:
        return ""
    
    def _render_table(self, element: MarkdownElement) -> str:
        return f"\n{self.box_tools.table_box(element.content)}\n\n"
    
    def _render_inline_content(self, content: List[Union[str, MarkdownElement]]) -> str:
        result = ""
        
        for item in content:
            if isinstance(item, str):
                result += item
            elif isinstance(item, MarkdownElement):
                if item.type == ElementType.BOLD:
                    result += f"{self.colors.BOLD_TEXT}{self._render_inline_content(item.content)}{self.colors.RESET}"
                elif item.type == ElementType.ITALIC:
                    result += f"{self.colors.ITALIC_TEXT}{self._render_inline_content(item.content)}{self.colors.RESET}"
                elif item.type == ElementType.CODE:
                    result += f"{self.colors.CODE_TEXT}`{item.content}`{self.colors.RESET}"
                elif item.type == ElementType.LINK:
                    result += f"{self.colors.LINK_TEXT}{self._render_inline_content(item.content)}{self.colors.RESET} {self.colors.LINK_URL}[{item.url}]{self.colors.RESET}"
                elif item.type == ElementType.IMAGE:
                    alt_text = self._render_inline_content(item.content) if item.content else ""
                    image_path = item.url if item.url else ""
                    return self.image_renderer.render_image(image_path, alt_text)
                elif item.type == ElementType.COMMENT:
                    result += f"{self.colors.COMMENT_TEXT}<!-- {item.content} -->{self.colors.RESET}"
        
        return result

def render_markdown(md_text: str, colored_output: bool = True, centered: bool = False) -> str:
    import sys
    
    # Generate the rendered markdown content
    renderer = EnhancedMarkdownRenderer(colored_output=colored_output)
    result = renderer.render(md_text)
    
    if centered:
        # Clear screen ANSI sequence
        clear_screen = "\033[2J\033[H"  # Clear screen and position cursor at top-left
        
        # Get terminal dimensions
        try:
            terminal_width, terminal_height = shutil.get_terminal_size()
        except (AttributeError, ValueError, OSError):
            terminal_width, terminal_height = 80, 24
        
        # Count lines in the rendered content
        rendered_lines = result.splitlines()
        content_height = len(rendered_lines)
        
        # Calculate vertical padding
        top_padding = max(0, (terminal_height - content_height) // 2)
        
        # Add vertical centering with empty lines at the top
        result = clear_screen + ("\n" * top_padding) + result
    
    return result

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], "r") as f:
                md_text = f.read()
        except FileNotFoundError:
            print(f"Error: File '{sys.argv[1]}' not found.")
            sys.exit(1)
    else:
        md_text = "# Markdown Example"
    
    print(render_markdown(md_text))
