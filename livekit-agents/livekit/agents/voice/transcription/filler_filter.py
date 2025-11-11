from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Iterable, Tuple

DEFAULT_FILLER_PHRASES: tuple[str, ...] = (
    "uh",
    "um",
    "uh huh",
    "uh-huh",
    "erm",
    "er",
    "hm",
    "hmm",
    "mm",
    "mmm",
    "mm hmm",
    "mm-hmm",
    "ah",
    "oh",
    "huh",
    "hmmm",
    "mhm",
)

_TOKEN_PATTERN = re.compile(r"[a-zA-Z']+")


class FillerPhraseFilter:
    """Detects transcripts that consist entirely of filler words."""

    def __init__(self, phrases: Sequence[str] | None = None) -> None:
        self._normalized_phrases: set[tuple[str, ...]] = set()
        self._max_phrase_len: int = 0
        self.update_phrases(phrases)

    def update_phrases(self, phrases: Sequence[str] | None) -> None:
        """Replace the filler phrases used by the detector."""
        normalized_phrases = set()
        max_len = 0

        iterable: Iterable[str]
        if phrases is None:
            iterable = DEFAULT_FILLER_PHRASES
        else:
            iterable = phrases

        for phrase in iterable:
            normalized = self._normalize_phrase(phrase)
            if not normalized:
                continue
            normalized_tuple = tuple(normalized)
            normalized_phrases.add(normalized_tuple)
            max_len = max(max_len, len(normalized_tuple))

        self._normalized_phrases = normalized_phrases
        self._max_phrase_len = max_len

    def is_filler(self, text: str) -> bool:
        """Return True if the provided text contains only filler content."""
        if not self._normalized_phrases:
            return False

        tokens = self._tokenize(text)
        if not tokens:
            return False

        idx = 0
        length = len(tokens)

        while idx < length:
            matched = False
            max_window = min(self._max_phrase_len, length - idx)
            for window in range(max_window, 0, -1):
                candidate = tuple(tokens[idx : idx + window])
                if candidate in self._normalized_phrases:
                    idx += window
                    matched = True
                    break
            if not matched:
                return False

        return True

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [token for token in _TOKEN_PATTERN.findall(text.lower()) if token]

    @classmethod
    def _normalize_phrase(cls, phrase: str) -> Tuple[str, ...]:
        return tuple(cls._tokenize(phrase))
