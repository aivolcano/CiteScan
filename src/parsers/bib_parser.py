"""
BibTeX file parser.
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode


@dataclass
class BibEntry:
    """Represents a parsed bibliography entry."""
    key: str
    entry_type: str
    title: str = ""
    author: str = ""
    year: str = ""
    abstract: str = ""
    url: str = ""
    doi: str = ""
    arxiv_id: str = ""
    journal: str = ""
    booktitle: str = ""
    publisher: str = ""
    pages: str = ""
    volume: str = ""
    number: str = ""
    raw_entry: dict = field(default_factory=dict)
    
    @property
    def has_arxiv(self) -> bool:
        """Check if entry has arXiv information."""
        return bool(self.arxiv_id)
    
    @property
    def search_query(self) -> str:
        """Get search query for this entry."""
        return self.title or self.key


class BibParser:
    """Parser for .bib files."""
    
    # Patterns for extracting arXiv IDs
    ARXIV_PATTERNS = [
        # New format: 2301.00001 or 2301.00001v1
        r'(\d{4}\.\d{4,5}(?:v\d+)?)',
        # Old format: hep-th/9901001 or math.GT/0309136
        r'([a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)',
        # arXiv: prefix
        r'arXiv:(\d{4}\.\d{4,5}(?:v\d+)?)',
        r'arXiv:([a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)',
    ]
    
    # URL patterns for arXiv
    ARXIV_URL_PATTERNS = [
        r'arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)',
        r'arxiv\.org/abs/([a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)',
        r'arxiv\.org/pdf/(\d{4}\.\d{4,5}(?:v\d+)?)(?:\.pdf)?',
        r'arxiv\.org/pdf/([a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)(?:\.pdf)?',
    ]
    
    def __init__(self):
        self.entries: list[BibEntry] = []
    
    def parse_file(self, filepath: str) -> list[BibEntry]:
        """Parse a .bib file into a list of entries."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Bib file not found: {filepath}")
        
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> list[BibEntry]:
        """Parse bib content string into a list of entries."""
        parser = BibTexParser(common_strings=True)
        parser.customization = convert_to_unicode
        
        try:
            bib_database = bibtexparser.loads(content, parser=parser)
        except Exception as e:
            raise ValueError(f"Failed to parse bib content: {e}")
        
        self.entries = []
        for entry in bib_database.entries:
            bib_entry = self._convert_entry(entry)
            self.entries.append(bib_entry)
        
        return self.entries
    
    def _convert_entry(self, entry: dict) -> BibEntry:
        """Convert a bibtexparser entry to BibEntry."""
        # Extract basic fields
        bib_entry = BibEntry(
            key=entry.get('ID', ''),
            entry_type=entry.get('ENTRYTYPE', ''),
            title=entry.get('title', ''),
            author=entry.get('author', ''),
            year=entry.get('year', ''),
            abstract=entry.get('abstract', ''),
            url=entry.get('url', ''),
            doi=entry.get('doi', ''),
            journal=entry.get('journal', ''),
            booktitle=entry.get('booktitle', ''),
            publisher=entry.get('publisher', ''),
            pages=entry.get('pages', ''),
            volume=entry.get('volume', ''),
            number=entry.get('number', ''),
            raw_entry=entry.copy()
        )
        
        # Extract arXiv ID
        bib_entry.arxiv_id = self._extract_arxiv_id(entry)
        
        return bib_entry
    
    def _extract_arxiv_id(self, entry: dict) -> str:
        """Extract arXiv ID from entry."""
        # Check eprint field first
        eprint = entry.get('eprint', '')
        if eprint:
            arxiv_id = self._parse_arxiv_id(eprint)
            if arxiv_id:
                return arxiv_id
        
        # Check arxiv field
        arxiv = entry.get('arxiv', '')
        if arxiv:
            arxiv_id = self._parse_arxiv_id(arxiv)
            if arxiv_id:
                return arxiv_id
        
        # Check URL field
        url = entry.get('url', '')
        if url:
            for pattern in self.ARXIV_URL_PATTERNS:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        # Check journal field for "arXiv preprint arXiv:XXXX.XXXXX" format
        journal = entry.get('journal', '')
        if journal and 'arxiv' in journal.lower():
            arxiv_id = self._parse_arxiv_id(journal)
            if arxiv_id:
                return arxiv_id
        
        # Check note field
        note = entry.get('note', '')
        if note:
            arxiv_id = self._parse_arxiv_id(note)
            if arxiv_id:
                return arxiv_id
        
        return ""
    
    def _parse_arxiv_id(self, text: str) -> str:
        """Parse arXiv ID from text."""
        for pattern in self.ARXIV_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return ""
    
    def get_entry_by_key(self, key: str) -> Optional[BibEntry]:
        """Get entry by citation key."""
        for entry in self.entries:
            if entry.key == key:
                return entry
        return None

    def filter_file(self, input_path: str, output_path: str, keys_to_keep: set[str]):
        """
        Create a new bib file containing only specified keys.
        Preserves original formatting, comments, and strings.
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        filtered_content = self._filter_content(content, keys_to_keep)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(filtered_content)
            
    def _filter_content(self, content: str, keys_to_keep: set[str]) -> str:
        """Filter content string keeping only specified keys."""
        ranges_to_remove = []
        i = 0
        length = len(content)
        
        while i < length:
            if content[i] == '@':
                start = i
                # Find opening brace
                brace_open = content.find('{', i)
                if brace_open == -1:
                    i += 1
                    continue
                
                # Get entry type
                entry_type = content[i+1:brace_open].strip().lower()
                
                # Skip comments
                if entry_type == 'comment':
                    i = brace_open + 1
                    continue
                
                # Find matching closing brace to determine entry end
                balance = 1
                j = brace_open + 1
                in_quote = False
                
                while j < length and balance > 0:
                    char = content[j]
                    
                    # Handle escaped characters
                    if char == '\\':
                        j += 2
                        continue
                        
                    if char == '"':
                        in_quote = not in_quote
                    elif not in_quote:
                        if char == '{':
                            balance += 1
                        elif char == '}':
                            balance -= 1
                    j += 1
                
                end = j
                
                # Extract key (between { and ,)
                # Only for standard entries, not @string or @preamble
                if entry_type not in ('string', 'preamble'):
                    # Find comma or end of entry
                    # Key is usually the first token after {
                    key_part = content[brace_open+1:end]
                    comma_pos = key_part.find(',')
                    
                    if comma_pos != -1:
                        key = key_part[:comma_pos].strip()
                        
                        # If key is NOT in keep list, mark for removal
                        if key not in keys_to_keep:
                            ranges_to_remove.append((start, end))
                
                i = end
            else:
                i += 1
        
        # Reconstruct content
        new_content = []
        last_pos = 0
        for start, end in ranges_to_remove:
            new_content.append(content[last_pos:start])
            
            # Clean up whitespace after removed entry
            last_pos = end
            while last_pos < length and content[last_pos] in ' \t\r':
                last_pos += 1
            if last_pos < length and content[last_pos] == '\n':
                last_pos += 1
        
        new_content.append(content[last_pos:])
        return "".join(new_content)

