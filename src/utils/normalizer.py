"""
Text normalization utilities for comparing bibliography entries.
"""
import re
import unicodedata
from unidecode import unidecode


class TextNormalizer:
    """Utility class for normalizing text for comparison."""
    
    # LaTeX command patterns
    LATEX_COMMANDS = [
        (r'\\textbf\{([^}]*)\}', r'\1'),
        (r'\\textit\{([^}]*)\}', r'\1'),
        (r'\\emph\{([^}]*)\}', r'\1'),
        (r'\\textrm\{([^}]*)\}', r'\1'),
        (r'\\texttt\{([^}]*)\}', r'\1'),
        (r'\\textsf\{([^}]*)\}', r'\1'),
        (r'\\textsc\{([^}]*)\}', r'\1'),
        (r'\\text\{([^}]*)\}', r'\1'),
        (r'\\mathrm\{([^}]*)\}', r'\1'),
        (r'\\mathbf\{([^}]*)\}', r'\1'),
        (r'\\mathit\{([^}]*)\}', r'\1'),
        (r'\\url\{([^}]*)\}', r'\1'),
        (r'\\href\{[^}]*\}\{([^}]*)\}', r'\1'),
    ]
    
    # LaTeX special character mappings
    LATEX_CHARS = {
        r'\&': '&',
        r'\%': '%',
        r'\$': '$',
        r'\#': '#',
        r'\_': '_',
        r'\{': '{',
        r'\}': '}',
        r'\~': '~',
        r'\^': '^',
        r'``': '"',
        r"''": '"',
        r'`': "'",
        r"'": "'",
        r'--': '–',
        r'---': '—',
    }
    
    # LaTeX accent commands
    LATEX_ACCENTS = [
        (r"\\'([aeiouAEIOU])", r'\1'),  # acute
        (r'\\`([aeiouAEIOU])', r'\1'),   # grave
        (r'\\^([aeiouAEIOU])', r'\1'),   # circumflex
        (r'\\"([aeiouAEIOU])', r'\1'),   # umlaut
        (r'\\~([nNaAoO])', r'\1'),       # tilde
        (r'\\c\{([cC])\}', r'\1'),       # cedilla
        (r"\\'{([aeiouAEIOU])}", r'\1'),
        (r'\\`{([aeiouAEIOU])}', r'\1'),
        (r'\\^{([aeiouAEIOU])}', r'\1'),
        (r'\\"{([aeiouAEIOU])}', r'\1'),
        (r'\\~{([nNaAoO])}', r'\1'),
    ]
    
    @classmethod
    def normalize_latex(cls, text: str) -> str:
        """Remove LaTeX formatting commands."""
        if not text:
            return ""
        
        result = text
        
        # Remove LaTeX commands
        for pattern, replacement in cls.LATEX_COMMANDS:
            result = re.sub(pattern, replacement, result)
        
        # Handle LaTeX accents
        for pattern, replacement in cls.LATEX_ACCENTS:
            result = re.sub(pattern, replacement, result)
        
        # Replace LaTeX special characters
        for latex_char, normal_char in cls.LATEX_CHARS.items():
            result = result.replace(latex_char, normal_char)
        
        # Remove remaining braces
        result = re.sub(r'[{}]', '', result)
        
        return result
    
    @classmethod
    def normalize_unicode(cls, text: str) -> str:
        """Normalize Unicode characters to ASCII."""
        if not text:
            return ""
        
        # Normalize unicode
        text = unicodedata.normalize('NFKD', text)
        # Convert to ASCII
        text = unidecode(text)
        return text
    
    @classmethod
    def normalize_whitespace(cls, text: str) -> str:
        """Normalize whitespace."""
        if not text:
            return ""
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text
    
    @classmethod
    def remove_punctuation(cls, text: str) -> str:
        """Remove punctuation for comparison."""
        if not text:
            return ""
        
        # Keep alphanumeric and spaces only
        return re.sub(r'[^\w\s]', '', text)
    
    @classmethod
    def normalize_for_comparison(cls, text: str) -> str:
        """
        Full normalization pipeline for text comparison.
        
        Steps:
        1. Remove LaTeX formatting
        2. Normalize Unicode to ASCII
        3. Convert to lowercase
        4. Normalize whitespace
        5. Remove punctuation
        """
        if not text:
            return ""
        
        text = cls.normalize_latex(text)
        text = cls.normalize_unicode(text)
        text = text.lower()
        text = cls.normalize_whitespace(text)
        text = cls.remove_punctuation(text)
        return text
    
    @classmethod
    def normalize_author_name(cls, name: str) -> str:
        """
        Normalize author name format.
        Handles: "Last, First" and "First Last" formats.
        Returns: normalized "first last" format.
        """
        if not name:
            return ""
        
        name = cls.normalize_latex(name)
        name = cls.normalize_unicode(name)
        name = cls.normalize_whitespace(name)
        
        # Handle "Last, First" format
        if ',' in name:
            parts = name.split(',', 1)
            if len(parts) == 2:
                name = f"{parts[1].strip()} {parts[0].strip()}"
        
        name = name.lower()
        name = cls.remove_punctuation(name)
        return name
    
    @classmethod
    def normalize_author_list(cls, authors: str) -> list[str]:
        """
        Parse and normalize a list of authors.
        Handles "and" as separator and "Last, First" format.
        """
        if not authors:
            return []
        
        # Split by " and "
        author_list = re.split(r'\s+and\s+', authors, flags=re.IGNORECASE)
        
        # Normalize each author
        normalized = []
        for author in author_list:
            normalized_name = cls.normalize_author_name(author.strip())
            if normalized_name:
                normalized.append(normalized_name)
        
        return normalized
    
    @classmethod
    def similarity_ratio(cls, text1: str, text2: str) -> float:
        """Calculate word-based Jaccard similarity ratio between two strings."""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    @classmethod
    def levenshtein_similarity(cls, s1: str, s2: str) -> float:
        """Calculate normalized Levenshtein similarity."""
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        
        # Simple Levenshtein implementation
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) + 1
        
        max_len = max(m, n)
        distance = dp[m][n]
        return 1.0 - (distance / max_len)
