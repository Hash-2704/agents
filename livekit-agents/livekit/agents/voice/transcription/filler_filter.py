"""Filter for detecting and handling filler-only speech segments."""
from __future__ import annotations

import re
from dataclasses import dataclass
from threading import RLock
from typing import Sequence


# Default list of common filler words across multiple languages
DEFAULT_FILLER_WORDS = [
    # English fillers
    "uh", "um", "hmm", "hm", "ah", "er", "erm", "like", "you know", "i mean", "well",
    "so", "actually", "basically", "literally", "right", "okay", "ok", "yeah", "yep",
    "yup", "nope", "nah", "meh", "oof", "ouch", "oops", "whoops", "geez",
    # Spanish fillers
    "eh", "este", "pues", "bueno", "entonces", "vale",
    # French fillers
    "euh", "bah", "ben", "bof", "hein", "quoi", "voilà",
    # German fillers
    "äh", "ähm", "also", "halt", "eben", "quasi", "sozusagen",
    # Portuguese fillers
    "né", "tipo", "então", "ahn", "hum",
    # Italian fillers
    "ehm", "cioè", "praticamente", "insomma",
    # Japanese fillers (romanized)
    "ano", "eto", "nanka", "ma",
    # Chinese fillers (pinyin)
    "en", "na", "nage", "zhege",
]


@dataclass
class FillerFilterResult:
    """Result of filler filtering analysis."""
    is_filler_only: bool
    """Whether the text contains only filler words."""
    text: str
    """The original text."""
    filtered_words: list[str]
    """Words that were identified as fillers."""
    non_filler_words: list[str]
    """Words that were not identified as fillers."""


class FillerWordsFilter:
    """Filter to detect if speech segments contain only filler words.
    
    This filter is thread-safe and can be used to prevent false interruptions
    when users make filler sounds while thinking but aren't actually trying
    to interrupt the agent.
    
    Args:
        filler_words: List of words to consider as fillers. Defaults to a
            comprehensive list covering multiple languages.
        case_sensitive: Whether matching should be case-sensitive. Default False.
        allow_punctuation: Whether to allow punctuation around filler words.
            Default True.
    
    Example:
        ```python
        filter = FillerWordsFilter()
        result = filter.is_filler_only("um... uh, hmm")
        if result.is_filler_only:
            print("Ignoring filler-only speech")
        ```
    """
    
    def __init__(
        self,
        filler_words: Sequence[str] | None = None,
        case_sensitive: bool = False,
        allow_punctuation: bool = True,
    ):
        self._filler_words = set(filler_words if filler_words else DEFAULT_FILLER_WORDS)
        self._case_sensitive = case_sensitive
        self._allow_punctuation = allow_punctuation
        self._lock = RLock()
        
        if not self._case_sensitive:
            self._filler_words = {w.lower() for w in self._filler_words}
    
    def update_filler_words(self, filler_words: Sequence[str]) -> None:
        """Update the list of filler words dynamically (thread-safe).
        
        Args:
            filler_words: New list of filler words to use.
        """
        with self._lock:
            self._filler_words = set(filler_words)
            if not self._case_sensitive:
                self._filler_words = {w.lower() for w in self._filler_words}
    
    def add_filler_words(self, words: Sequence[str]) -> None:
        """Add additional filler words to the existing list (thread-safe).
        
        Args:
            words: Additional filler words to add.
        """
        with self._lock:
            words_to_add = set(words)
            if not self._case_sensitive:
                words_to_add = {w.lower() for w in words_to_add}
            self._filler_words.update(words_to_add)
    
    def remove_filler_words(self, words: Sequence[str]) -> None:
        """Remove filler words from the list (thread-safe).
        
        Args:
            words: Filler words to remove.
        """
        with self._lock:
            words_to_remove = set(words)
            if not self._case_sensitive:
                words_to_remove = {w.lower() for w in words_to_remove}
            self._filler_words.difference_update(words_to_remove)
    
    def get_filler_words(self) -> set[str]:
        """Get the current list of filler words (thread-safe).
        
        Returns:
            Set of filler words currently in use.
        """
        with self._lock:
            return self._filler_words.copy()
    
    def is_filler_only(self, text: str) -> FillerFilterResult:
        """Check if the given text contains only filler words.
        
        Args:
            text: The text to check.
        
        Returns:
            FillerFilterResult with detailed analysis.
        """
        if not text or not text.strip():
            return FillerFilterResult(
                is_filler_only=True,
                text=text,
                filtered_words=[],
                non_filler_words=[]
            )
        
        # Normalize text
        normalized = text
        if not self._case_sensitive:
            normalized = text.lower()
        
        with self._lock:
            # First, check for multi-word filler phrases
            remaining_text = normalized
            filler_words_found = []
            
            # Sort filler words by length (longest first) to match multi-word phrases first
            sorted_fillers = sorted(self._filler_words, key=len, reverse=True)
            
            for filler in sorted_fillers:
                if ' ' in filler:  # Multi-word phrase
                    # Use word boundaries to match whole phrases
                    pattern = r'\b' + re.escape(filler) + r'\b'
                    matches = re.finditer(pattern, remaining_text)
                    for match in matches:
                        filler_words_found.append(match.group())
                        # Replace matched phrase with spaces to avoid re-matching
                        remaining_text = remaining_text[:match.start()] + ' ' * len(match.group()) + remaining_text[match.end():]
            
            # Now extract remaining words
            if self._allow_punctuation:
                words = re.findall(r'\b[\w\']+\b', remaining_text)
            else:
                words = remaining_text.split()
            
            non_filler_words_found = []
            
            for word in words:
                if not word or word.isspace():
                    continue
                    
                word_clean = word.strip("'\".,;:!?")
                
                if word_clean in self._filler_words or word in self._filler_words:
                    filler_words_found.append(word)
                else:
                    non_filler_words_found.append(word)
        
        is_filler_only = len(non_filler_words_found) == 0
        
        return FillerFilterResult(
            is_filler_only=is_filler_only,
            text=text,
            filtered_words=filler_words_found,
            non_filler_words=non_filler_words_found
        )
