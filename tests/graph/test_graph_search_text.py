"""build_search_text: name plus the string values of the public props only."""

from cac_common.search_text import build_search_text


def test_name_and_public_string_props_only():
    props = {"description": "Rich and creamy.", "supplier": "Acme Kegs", "price_cents": 900}
    text = build_search_text("Guinness", props, ["description", "price_cents"])
    assert text == "Guinness Rich and creamy."


def test_lists_are_joined_with_spaces():
    props = {"schema_org": "VegetarianDiet", "synonyms": ["veggie", "no meat"]}
    text = build_search_text("Vegetarian", props, ["schema_org", "synonyms"])
    assert text == "Vegetarian VegetarianDiet veggie no meat"


def test_numbers_bools_and_nulls_are_skipped():
    props = {"closed": True, "date": "2026-11-26", "opens": None, "position": 3, "ratio": 1.5}
    text = build_search_text("Thanksgiving", props, ["date", "closed", "opens", "position"])
    assert text == "Thanksgiving 2026-11-26"


def test_nested_values_are_flattened_to_string_leaves():
    props = {
        "binds": {"labels": ["Service"], "min": 1, "max": 1},
        "fields": [{"name": "email", "required": True, "options": ["a", "b"]}],
    }
    text = build_search_text("Contact", props, ["binds", "fields"])
    assert text == "Contact Service email a b"


def test_single_spaced_and_follows_public_props_order():
    props = {"b": "two\n  words", "a": "  first "}
    assert build_search_text(" The  Name ", props, ["a", "b"]) == "The Name first two words"


def test_missing_public_prop_is_ignored():
    assert build_search_text("Milk", {}, ["fda_major", "synonyms"]) == "Milk"
