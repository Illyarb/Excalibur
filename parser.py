import re
from enum import Enum, auto
from typing import List, Optional, Tuple, Union, Dict


class ElementType(Enum):
    HEADING = auto()
    PARAGRAPH = auto()
    BOLD = auto()
    ITALIC = auto()
    CODE = auto()
    CODE_BLOCK = auto()
    LINK = auto()
    IMAGE = auto()
    DASH_LIST = auto()
    ASTERISK_LIST = auto()
    PLUS_LIST = auto()
    ORDERED_LIST = auto()
    BLOCKQUOTE = auto()
    DASH_RULE = auto()
    ASTERISK_RULE = auto()
    UNDERSCORE_RULE = auto()
    TEXT = auto()
    COMMENT = auto()  # New element type for HTML comments
    TABLE = auto()    # New element type for tables


class MarkdownElement:
    def __init__(self, element_type: ElementType, content=None, level=0, url=None):
        self.type = element_type
        self.content = content or []
        self.level = level
        self.url = url


class TableCell:
    def __init__(self, content, is_header=False, alignment=None):
        self.content = content
        self.is_header = is_header
        self.alignment = alignment  # 'left', 'center', 'right', or None


class Table:
    def __init__(self, headers=None, rows=None, alignments=None):
        self.headers = headers or []
        self.rows = rows or []
        self.alignments = alignments or []  # List of alignment strings for each column


class MarkdownParser:
    def __init__(self):
        self.elements = []
    
    def parse(self, text: str) -> List[MarkdownElement]:
        self.elements = []
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Handle empty lines
            if not line.strip():
                i += 1
                continue
            
            # Handle HTML comments
            comment_match = re.match(r'^\s*<!--(.*?)-->\s*$', line)
            if comment_match:
                content = comment_match.group(1).strip()
                self.elements.append(MarkdownElement(ElementType.COMMENT, content))
                i += 1
                continue
            
            # Handle multi-line HTML comments
            if '<!--' in line and '-->' not in line:
                comment_lines = [line[line.find('<!--')+4:]]
                i += 1
                while i < len(lines) and '-->' not in lines[i]:
                    comment_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    comment_lines.append(lines[i][:lines[i].find('-->')])
                    i += 1
                content = '\n'.join(comment_lines).strip()
                self.elements.append(MarkdownElement(ElementType.COMMENT, content))
                continue
            
            # Handle tables - check for table header and separator
            if i + 1 < len(lines) and '|' in line and '|' in lines[i+1] and re.match(r'^\s*\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$', lines[i+1]):
                table_result = self._parse_table(lines, i)
                if table_result:
                    table_element, next_line = table_result
                    self.elements.append(table_element)
                    i = next_line
                    continue
            
            # Handle headings
            heading_match = re.match(r'^(#{1,6})\s+(.*?)(?:\s+#+)?$', line)
            if heading_match:
                level = len(heading_match.group(1))
                content = self._parse_inline(heading_match.group(2).strip())
                self.elements.append(MarkdownElement(ElementType.HEADING, content, level))
                i += 1
                continue
            
            # Handle horizontal rules
            hr_match = re.match(r'^(\*{3,}|-{3,}|_{3,})$', line)
            if hr_match:
                marker = hr_match.group(1)[0]
                if marker == '-':
                    self.elements.append(MarkdownElement(ElementType.DASH_RULE))
                elif marker == '*':
                    self.elements.append(MarkdownElement(ElementType.ASTERISK_RULE))
                elif marker == '_':
                    self.elements.append(MarkdownElement(ElementType.UNDERSCORE_RULE))
                i += 1
                continue
            
            # Handle code blocks
            if line.startswith('```'):
                code_block = []
                language = line[3:].strip()
                i += 1
                while i < len(lines) and not lines[i].startswith('```'):
                    code_block.append(lines[i])
                    i += 1
                if i < len(lines):  # Skip the closing ```
                    i += 1
                element = MarkdownElement(ElementType.CODE_BLOCK, '\n'.join(code_block))
                element.language = language if language else None
                self.elements.append(element)
                continue
            
            # Handle blockquotes
            if line.startswith('>'):
                quote_lines = []
                while i < len(lines) and lines[i].startswith('>'):
                    quote_lines.append(lines[i][1:].strip())
                    i += 1
                content = self._parse_inline(' '.join(quote_lines))
                self.elements.append(MarkdownElement(ElementType.BLOCKQUOTE, content))
                continue
            
            # Handle dash lists
            if re.match(r'^\s*-\s', line):
                list_items = []
                while i < len(lines) and re.match(r'^\s*-\s', lines[i]):
                    item_content = re.sub(r'^\s*-\s', '', lines[i])
                    list_items.append(self._parse_inline(item_content))
                    i += 1
                self.elements.append(MarkdownElement(ElementType.DASH_LIST, list_items))
                continue
            
            # Handle asterisk lists
            if re.match(r'^\s*\*\s', line):
                list_items = []
                while i < len(lines) and re.match(r'^\s*\*\s', lines[i]):
                    item_content = re.sub(r'^\s*\*\s', '', lines[i])
                    list_items.append(self._parse_inline(item_content))
                    i += 1
                self.elements.append(MarkdownElement(ElementType.ASTERISK_LIST, list_items))
                continue
            
            # Handle plus lists
            if re.match(r'^\s*\+\s', line):
                list_items = []
                while i < len(lines) and re.match(r'^\s*\+\s', lines[i]):
                    item_content = re.sub(r'^\s*\+\s', '', lines[i])
                    list_items.append(self._parse_inline(item_content))
                    i += 1
                self.elements.append(MarkdownElement(ElementType.PLUS_LIST, list_items))
                continue
            
            # Handle ordered lists
            if re.match(r'^\s*\d+\.\s', line):
                list_items = []
                while i < len(lines) and re.match(r'^\s*\d+\.\s', lines[i]):
                    item_content = re.sub(r'^\s*\d+\.\s', '', lines[i])
                    list_items.append(self._parse_inline(item_content))
                    i += 1
                self.elements.append(MarkdownElement(ElementType.ORDERED_LIST, list_items))
                continue
            
            # Handle images that are on their own line
            image_match = re.match(r'^\s*!\[(.*?)\]\((.*?)\)\s*$', line)
            if image_match:
                alt_text = image_match.group(1)
                image_url = image_match.group(2)
                element = MarkdownElement(ElementType.IMAGE, self._parse_inline(alt_text), url=image_url)
                self.elements.append(element)
                i += 1
                continue
            
            # Handle paragraphs
            paragraph_lines = []
            while i < len(lines) and lines[i].strip() and not (
                    lines[i].startswith('#') or
                    lines[i].startswith('```') or
                    lines[i].startswith('>') or
                    lines[i].startswith('<!--') or
                    ('|' in lines[i] and i + 1 < len(lines) and
                     '|' in lines[i+1] and re.match(r'^\s*\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$', lines[i+1])) or
                    re.match(r'^\s*[-*+]\s', lines[i]) or
                    re.match(r'^\s*\d+\.\s', lines[i]) or
                    re.match(r'^(\*{3,}|-{3,}|_{3,})$', lines[i]) or
                    re.match(r'^\s*!\[(.*?)\]\((.*?)\)\s*$', lines[i])
            ):
                paragraph_lines.append(lines[i])
                i += 1
            
            if paragraph_lines:
                content = self._parse_inline(' '.join(paragraph_lines))
                self.elements.append(MarkdownElement(ElementType.PARAGRAPH, content))
                continue
            
            # If we get here, we couldn't parse the line, so treat as plain text
            self.elements.append(MarkdownElement(ElementType.TEXT, [line]))
            i += 1
        
        return self.elements
    
    def _parse_table(self, lines: List[str], start_index: int) -> Optional[Tuple[MarkdownElement, int]]:
        """Parse a markdown table and return the table element and the next line index"""
        if start_index + 1 >= len(lines):
            return None
        
        # Parse header row
        header_line = lines[start_index]
        # Parse separator row (determines column alignment)
        separator_line = lines[start_index + 1]
        
        # Check if valid separator line
        if not re.match(r'^\s*\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$', separator_line):
            return None
        
        # Process header cells
        header_cells = self._split_table_row(header_line)
        if not header_cells:
            return None
        
        # Process separator cells to determine alignment
        separator_cells = self._split_table_row(separator_line)
        alignments = []
        for cell in separator_cells:
            cell = cell.strip()
            if cell.startswith(':') and cell.endswith(':'):
                alignments.append('center')
            elif cell.startswith(':'):
                alignments.append('left')
            elif cell.endswith(':'):
                alignments.append('right')
            else:
                alignments.append('left')  # Default alignment
        
        # Process headers with parsed inline content
        headers = []
        for i, cell in enumerate(header_cells):
            alignment = alignments[i] if i < len(alignments) else 'left'
            cell_content = self._parse_inline(cell.strip())
            headers.append(TableCell(cell_content, is_header=True, alignment=alignment))
        
        # Process data rows
        rows = []
        current_index = start_index + 2
        while current_index < len(lines) and '|' in lines[current_index]:
            row_cells = self._split_table_row(lines[current_index])
            if not row_cells:
                break
            
            row = []
            for i, cell in enumerate(row_cells):
                alignment = alignments[i] if i < len(alignments) else 'left'
                cell_content = self._parse_inline(cell.strip())
                row.append(TableCell(cell_content, is_header=False, alignment=alignment))
            
            rows.append(row)
            current_index += 1
        
        # Create table content
        table = Table(headers=headers, rows=rows, alignments=alignments)
        element = MarkdownElement(ElementType.TABLE, table)
        
        return element, current_index
    
    def _split_table_row(self, row: str) -> List[str]:
        """Split a table row into individual cells"""
        # Remove leading and trailing pipe if present
        if row.strip().startswith('|'):
            row = row.strip()[1:]
        if row.strip().endswith('|'):
            row = row.strip()[:-1]
        
        # Split by pipe, but respect escaped pipes
        cells = []
        current_cell = ""
        escape_active = False
        for char in row:
            if char == '\\' and not escape_active:
                escape_active = True
                continue
            
            if char == '|' and not escape_active:
                cells.append(current_cell)
                current_cell = ""
            else:
                current_cell += char
                escape_active = False
        
        cells.append(current_cell)
        return cells
    
    def _parse_inline(self, text: str) -> List[Union[str, MarkdownElement]]:
        if not text:
            return []
        
        result = []
        remaining_text = text
        
        while remaining_text:
            # Check for inline HTML comments
            comment_match = re.search(r'<!--(.*?)-->', remaining_text)
            # Image
            image_match = re.search(r'!\[(.*?)\]\((.*?)\)', remaining_text)
            # Bold
            bold_match = re.search(r'(\*\*|__)(.*?)\1', remaining_text)
            # Italic
            italic_match = re.search(r'(\*|_)((?!\1).*?)\1', remaining_text)
            # Code
            code_match = re.search(r'`(.*?)`', remaining_text)
            # Link
            link_match = re.search(r'\[(.*?)\]\((.*?)\)', remaining_text)
            
            matches = [m for m in [comment_match, image_match, bold_match, italic_match, code_match, link_match] if m]
            
            if not matches:
                result.append(remaining_text)
                break
            
            earliest_match = min(matches, key=lambda m: m.start())
            
            # Add text before the match
            if earliest_match.start() > 0:
                result.append(remaining_text[:earliest_match.start()])
            
            # Process the match
            if earliest_match == comment_match:
                content = earliest_match.group(1).strip()
                result.append(MarkdownElement(ElementType.COMMENT, content))
            elif earliest_match == image_match:
                alt_text = self._parse_inline(earliest_match.group(1))
                url = earliest_match.group(2)
                result.append(MarkdownElement(ElementType.IMAGE, alt_text, url=url))
            elif earliest_match == bold_match:
                content = self._parse_inline(earliest_match.group(2))
                result.append(MarkdownElement(ElementType.BOLD, content))
            elif earliest_match == italic_match:
                content = self._parse_inline(earliest_match.group(2))
                result.append(MarkdownElement(ElementType.ITALIC, content))
            elif earliest_match == code_match:
                result.append(MarkdownElement(ElementType.CODE, earliest_match.group(1)))
            elif earliest_match == link_match:
                text_content = self._parse_inline(earliest_match.group(1))
                url = earliest_match.group(2)
                result.append(MarkdownElement(ElementType.LINK, text_content, url=url))
            
            # Continue with the remaining text
            remaining_text = remaining_text[earliest_match.end():]
        
        return result
