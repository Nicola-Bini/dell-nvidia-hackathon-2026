"""SCHEMA 8.2: normalizing is lowercase, trim, collapse whitespace, strip punctuation."""

from __future__ import annotations

import hashlib

from cac_serve.domain.normalize import normalize, normalized_hash


def test_normalize_schema_example():
    assert normalize("  Do you have  Gluten-Free pasta?? ") == "do you have gluten free pasta"


def test_normalize_apostrophes_join_and_other_punctuation_splits():
    assert normalize("What's on draft?") == "whats on draft"
    assert normalize("I’m allergic to peanuts!") == "im allergic to peanuts"
    assert normalize("nut-free\tdishes\n") == "nut free dishes"


def test_normalize_empty_and_punctuation_only():
    assert normalize("") == ""
    assert normalize(" ?!... ") == ""


def test_normalized_hash_is_sha256_of_the_normal_form():
    expected = hashlib.sha256(b"vegetarian options").hexdigest()
    assert normalized_hash("Vegetarian   options?") == expected
    assert normalized_hash("vegetarian options") == expected
    assert len(expected) == 64
