"""Text normal form (SCHEMA 8.2): lowercase, trim, collapse whitespace, strip punctuation.

The normal form is the cache key and the retrieval token source. It is never shown or logged.
"""

from __future__ import annotations

import hashlib
import re

_APOSTROPHES = re.compile(r"['‘’ʼ`]")
_NOT_WORD = re.compile(r"[^\w\s]|_")
_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    """"What's on  Draft?" -> "whats on draft"; a hyphen splits ("gluten-free" -> two words)."""
    lowered = _APOSTROPHES.sub("", text.lower())
    return _SPACES.sub(" ", _NOT_WORD.sub(" ", lowered)).strip()


def normalized_hash(text: str) -> str:
    """sha256 hex of the normal form."""
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()
