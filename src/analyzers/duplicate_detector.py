"""
Duplicate entry detector for bibliography files.
Uses fuzzy matching to find potential duplicates.
"""
from dataclasses import dataclass
from typing import List, Tuple

from ..parsers.bib_parser import BibEntry
from ..utils.normalizer import TextNormalizer


@dataclass
class DuplicateGroup:
    """A group of potentially duplicate entries."""
    entries: List[BibEntry]
    similarity_score: float
    reason: str
    
    @property
    def entry_keys(self) -> List[str]:
        return [e.key for e in self.entries]


class DuplicateDetector:
    """Detects duplicate bibliography entries using fuzzy matching."""
    
    # Thresholds for duplicate detection
    TITLE_SIMILARITY_THRESHOLD = 0.85
    COMBINED_SIMILARITY_THRESHOLD = 0.80
    
    def __init__(self):
        self.normalizer = TextNormalizer
    
    def find_duplicates(self, entries: List[BibEntry]) -> List[DuplicateGroup]:
        """
        Find all duplicate groups in the bibliography.
        
        Returns:
            List of DuplicateGroup objects, each containing 2+ similar entries.
        """
        duplicates = []
        processed = set()
        
        for i, entry1 in enumerate(entries):
            if entry1.key in processed:
                continue
            
            # Find all entries similar to this one
            similar_entries = [entry1]
            
            for j, entry2 in enumerate(entries[i+1:], start=i+1):
                if entry2.key in processed:
                    continue
                
                similarity, reason = self._calculate_similarity(entry1, entry2)
                
                if similarity >= self.COMBINED_SIMILARITY_THRESHOLD:
                    similar_entries.append(entry2)
                    processed.add(entry2.key)
            
            # If we found duplicates, create a group
            if len(similar_entries) > 1:
                processed.add(entry1.key)
                
                # Calculate average similarity for the group
                avg_similarity = self._calculate_group_similarity(similar_entries)
                reason = self._generate_reason(similar_entries)
                
                duplicates.append(DuplicateGroup(
                    entries=similar_entries,
                    similarity_score=avg_similarity,
                    reason=reason
                ))
        
        # Sort by similarity score (highest first)
        duplicates.sort(key=lambda g: g.similarity_score, reverse=True)
        
        return duplicates
    
    def _calculate_similarity(self, entry1: BibEntry, entry2: BibEntry) -> Tuple[float, str]:
        """
        Calculate similarity between two entries.
        
        Returns:
            (similarity_score, reason_string)
        """
        # Normalize titles
        title1 = self.normalizer.normalize_for_comparison(entry1.title)
        title2 = self.normalizer.normalize_for_comparison(entry2.title)
        
        # Calculate title similarity
        title_sim = self.normalizer.similarity_ratio(title1, title2)
        
        # If titles are very similar, likely a duplicate
        if title_sim >= self.TITLE_SIMILARITY_THRESHOLD:
            return title_sim, "Very similar titles"
        
        # Check author similarity
        author_sim = self._calculate_author_similarity(entry1, entry2)
        
        # Combined score: weighted average
        # Title is more important (70%) than authors (30%)
        combined_sim = 0.7 * title_sim + 0.3 * author_sim
        
        if combined_sim >= self.COMBINED_SIMILARITY_THRESHOLD:
            return combined_sim, f"Similar title ({title_sim:.0%}) and authors ({author_sim:.0%})"
        
        return combined_sim, ""
    
    def _calculate_author_similarity(self, entry1: BibEntry, entry2: BibEntry) -> float:
        """Calculate similarity between author lists."""
        # Parse author strings
        authors1 = self._parse_authors(entry1.author)
        authors2 = self._parse_authors(entry2.author)
        
        if not authors1 or not authors2:
            return 0.0
        
        # Normalize author names
        norm_authors1 = [self.normalizer.normalize_for_comparison(a) for a in authors1]
        norm_authors2 = [self.normalizer.normalize_for_comparison(a) for a in authors2]
        
        # Count matching authors
        matches = 0
        for a1 in norm_authors1:
            for a2 in norm_authors2:
                if self._authors_match(a1, a2):
                    matches += 1
                    break
        
        # Calculate Jaccard similarity
        total_unique = len(set(norm_authors1) | set(norm_authors2))
        if total_unique == 0:
            return 0.0
        
        return matches / total_unique
    
    def _parse_authors(self, author_string: str) -> List[str]:
        """Parse author string into list of names."""
        if not author_string:
            return []
        
        # Split by 'and'
        authors = author_string.split(' and ')
        
        # Clean up each author
        cleaned = []
        for author in authors:
            # Remove extra whitespace
            author = ' '.join(author.split())
            if author:
                cleaned.append(author)
        
        return cleaned
    
    def _authors_match(self, name1: str, name2: str) -> bool:
        """Check if two author names match (handles initials)."""
        # Simple exact match after normalization
        if name1 == name2:
            return True
        
        # Check if one is a substring of the other (handles initials)
        if name1 in name2 or name2 in name1:
            return True
        
        # Calculate string similarity
        sim = self.normalizer.similarity_ratio(name1, name2)
        return sim >= 0.8
    
    def _calculate_group_similarity(self, entries: List[BibEntry]) -> float:
        """Calculate average similarity within a group."""
        if len(entries) < 2:
            return 1.0
        
        total_sim = 0.0
        count = 0
        
        for i, entry1 in enumerate(entries):
            for entry2 in entries[i+1:]:
                sim, _ = self._calculate_similarity(entry1, entry2)
                total_sim += sim
                count += 1
        
        return total_sim / count if count > 0 else 0.0
    
    def _generate_reason(self, entries: List[BibEntry]) -> str:
        """Generate a human-readable reason for the duplicate group."""
        # Check if all titles are very similar
        titles = [self.normalizer.normalize_for_comparison(e.title) for e in entries]
        
        # Calculate pairwise title similarities
        title_sims = []
        for i, t1 in enumerate(titles):
            for t2 in titles[i+1:]:
                title_sims.append(self.normalizer.similarity_ratio(t1, t2))
        
        avg_title_sim = sum(title_sims) / len(title_sims) if title_sims else 0.0
        
        if avg_title_sim >= 0.95:
            return "Nearly identical titles"
        elif avg_title_sim >= 0.85:
            return "Very similar titles"
        else:
            return "Similar titles and authors"
