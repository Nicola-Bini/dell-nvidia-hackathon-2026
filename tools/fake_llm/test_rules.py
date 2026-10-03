"""The fake model's keyword rules against a Kenmore-like schema and candidate list."""

from __future__ import annotations

import jsonschema
import pytest
from rules import parse_offer, select

CANDIDATES = [
    ("diet_vegetarian", "Diet", "Vegetarian", "synonyms: veggie, meatless, no meat"),
    ("diet_gluten_free", "Diet", "Gluten-free", "synonyms: gf, gluten free, celiac"),
    ("alg_tree_nuts", "Allergen", "Tree nuts", "synonyms: nuts, almond, walnut"),
    ("alg_peanuts", "Allergen", "Peanuts", "synonyms: peanut, nut allergy"),
    ("alg_wheat", "Allergen", "Wheat", "synonyms: gluten, flour"),
    ("sec_draft_beer", "MenuSection", "Draft Beer", "14 items"),
    ("sec_ipas", "MenuSection", "IPAs", "15 items"),
    ("sec_sours", "MenuSection", "Sours", "15 items"),
    ("sec_porters_stouts", "MenuSection", "Porters & Stouts", "1 items"),
    ("sec_white_wine", "MenuSection", "White Wine", "5 items"),
    ("sec_red_wine", "MenuSection", "Red Wine", "4 items"),
    ("sec_cocktails", "MenuSection", "Cocktails", "4 items"),
    ("sec_burgers", "MenuSection", "Burgers", "8 items"),
    ("sec_hot_dogs", "MenuSection", "Hot Dogs", "6 items"),
    ("sec_appetizers_salads", "MenuSection", "Appetizers, Salads and More", "12 items"),
    ("mi_guinness", "MenuItem", "Guinness", "$9.00; Rich and creamy."),
    ("mi_chicken_wings", "MenuItem", "Chicken Wings", "$15.00; Buffalo or BBQ"),
    ("mi_chicken_tenders", "MenuItem", "Chicken Tenders", "$14.00"),
    ("mi_the_kenmore_burger", "MenuItem", 'The "Kenmore" Burger', "$16.00; House burger"),
    ("mi_shroom_lover_burger", "MenuItem", "Shroom Lover Burger", "$17.00; Mushrooms, swiss"),
    ("mi_the_brunch_dog", "MenuItem", "The Brunch Dog", "$12.00; Egg and bacon"),
    ("mi_the_veg_dog", "MenuItem", 'The Veg "Dog"', "$11.00; Beyond Meat sausage"),
    ("mi_voodoo_ranger_ipa", "MenuItem", "Voodoo Ranger IPA", "$8.00"),
    ("mi_destill_sour_pickle", "MenuItem", "Destill Sour Pickle", "$9.00"),
    ("faq_about", "FAQ", "What is The Kenmore?", "What is The Kenmore?"),
    ("faq_beer_selection", "FAQ", "What kind of beer and wine do you have?",
     "What kind of beer and wine do you have?"),
    ("faq_kitchen_hours", "FAQ", "When does the kitchen close?", "When does the kitchen close?"),
    ("faq_brunch", "FAQ", "Do you serve brunch?", "Do you serve brunch?"),
    ("faq_takeout_delivery", "FAQ", "Do you offer takeout or delivery?",
     "Do you offer takeout or delivery?"),
    ("faq_catering", "FAQ", "Do you cater events?", "Do you cater events?"),
    ("faq_private_events", "FAQ", "Can I host a private event?", "Can I host a private event?"),
    ("faq_burger_adds_sides", "FAQ", "What can I add to a burger, and what sides are there?",
     "What can I add to a burger, and what sides are there?"),
    ("faq_contact", "FAQ", "How do I contact The Kenmore?", "How do I contact The Kenmore?"),
    ("gc_standard", "GiftCard", "Standard gift card", "amounts: 25, 50"),
]
CANDIDATE_DICTS = [dict(zip(("id", "label", "name", "facts"), row, strict=True))
                   for row in CANDIDATES]

_GAP = {"type": "object", "additionalProperties": False, "required": ["kind", "topic"],
        "properties": {"kind": {"const": "gap"}, "topic": {"type": "string", "maxLength": 60}}}
_OFF = {"type": "object", "additionalProperties": False, "required": ["kind"],
        "properties": {"kind": {"const": "off_topic"}}}


def _variant(required: list[str], properties: dict) -> dict:
    return {"type": "object", "additionalProperties": False, "required": required,
            "properties": properties}


def _ids(prefix: str, candidates: list[dict]) -> list[str]:
    return [c["id"] for c in candidates if c["id"].startswith(prefix)]


def build_schema(candidates: list[dict], forms: tuple[str, ...] = ("ui_form_contact",),
                 labels: tuple[str, ...] = ()) -> dict:
    """A SCHEMA 8.1 schema for these candidates, following the schema-building rules."""
    if not candidates:
        return {"anyOf": [_GAP, _OFF]}
    menu_items: dict = {"type": "array", "maxItems": 6}
    if _ids("mi_", candidates):
        menu_items["items"] = {"enum": _ids("mi_", candidates)}
    else:
        menu_items["maxItems"] = 0
    views = [
        _variant(["component", "diet", "section", "items", "order"], {
            "component": {"const": "MenuList"},
            "diet": {"enum": [*_ids("diet_", candidates), None]},
            "section": {"enum": [*_ids("sec_", candidates), None]},
            "items": menu_items,
            "order": {"type": "boolean"},
        }),
        _variant(["component"], {
            "component": {"enum": ["HoursCard", "BookingForm", "CateringQuoteForm"]}}),
    ]
    if _ids("faq_", candidates):
        views.append(_variant(["component", "faq"], {
            "component": {"const": "Answer"}, "faq": {"enum": _ids("faq_", candidates)}}))
    if _ids("alg_", candidates):
        views.append(_variant(["component", "allergen"], {
            "component": {"const": "AllergenNotice"},
            "allergen": {"enum": _ids("alg_", candidates)}}))
    if forms:
        views.append(_variant(["component", "form"], {
            "component": {"const": "FormCard"}, "form": {"enum": list(forms)}}))
    if labels:
        views.append(_variant(["component", "label"], {
            "component": {"const": "ListCard"}, "label": {"enum": list(labels)}}))
        views.append(_variant(["component", "node"], {
            "component": {"const": "FactCard"}, "node": {"enum": _ids("gc_", candidates)}}))
    answer = _variant(["kind", "views"], {
        "kind": {"const": "answer"},
        "views": {"type": "array", "minItems": 1, "maxItems": 2, "items": {"anyOf": views}}})
    return {"anyOf": [answer, _GAP, _OFF]}


SCHEMA = build_schema(CANDIDATE_DICTS)


def _menu(diet=None, section=None, items=(), order=False) -> dict:
    return {"kind": "answer", "views": [{"component": "MenuList", "diet": diet,
                                         "section": section, "items": list(items),
                                         "order": order}]}


def _one(component: str, **fields: str) -> dict:
    return {"kind": "answer", "views": [{"component": component, **fields}]}


EXPECTED = [
    ("vegetarian options", _menu(diet="diet_vegetarian")),
    ("I want to pick up something vegetarian", _menu(diet="diet_vegetarian", order=True)),
    ("what burgers do you have?", _menu(section="sec_burgers")),
    ("show me the hot dogs", _menu(section="sec_hot_dogs")),
    ("what's on draft?", _menu(section="sec_draft_beer")),
    ("which IPAs do you have", _menu(section="sec_ipas")),
    ("any sour beers?", _menu(section="sec_sours")),
    ("do you have cocktails", _menu(section="sec_cocktails")),
    ("red wine by the glass", _menu(section="sec_red_wine")),
    ("do you have Guinness?", _menu(items=["mi_guinness"])),
    ("how much are the chicken wings", _menu(items=["mi_chicken_wings"])),
    ("what's in the Shroom Lover burger", _menu(items=["mi_shroom_lover_burger"])),
    ("is there a gluten free beer?", _menu(diet="diet_gluten_free")),
    ("is the veg dog vegetarian?", _menu(items=["mi_the_veg_dog"])),
    ("I'm allergic to peanuts", _one("AllergenNotice", allergen="alg_peanuts")),
    ("nut-free dishes", _one("AllergenNotice", allergen="alg_tree_nuts")),
    ("are you open tonight?", _one("HoursCard")),
    ("what time do you close on Saturday", _one("HoursCard")),
    ("are you open on the 4th of July?", _one("HoursCard")),
    ("are you open on Thanksgiving?", _one("HoursCard")),
    ("when does the kitchen close?", _one("Answer", faq="faq_kitchen_hours")),
    ("do you do brunch?", _one("Answer", faq="faq_brunch")),
    ("can I get delivery?", _one("Answer", faq="faq_takeout_delivery")),
    ("can I add bacon to my burger?", _one("Answer", faq="faq_burger_adds_sides")),
    ("can I host a birthday party there?", _one("Answer", faq="faq_private_events")),
    ("table for 4 on Friday at 7pm", _one("BookingForm")),
    ("do you cater for 40?", _one("CateringQuoteForm")),
    ("I'd like to send you a message", _one("FormCard", form="ui_form_contact")),
    ("is there parking nearby?", {"kind": "gap", "topic": "parking"}),
    ("tell me a joke", {"kind": "off_topic"}),
]


@pytest.mark.parametrize(("text", "expected"), EXPECTED, ids=[text for text, _ in EXPECTED])
def test_the_thirty_intents(text, expected):
    selection = select(SCHEMA, CANDIDATE_DICTS, text)
    jsonschema.validate(selection, SCHEMA)
    assert selection == expected


def test_gift_cards_pair_a_list_with_the_form():
    schema = build_schema(CANDIDATE_DICTS, forms=("ui_form_contact", "ui_form_gift_card"),
                          labels=("GiftCard",))
    selection = select(schema, CANDIDATE_DICTS, "do you sell gift cards?")
    jsonschema.validate(selection, schema)
    assert selection["views"] == [{"component": "ListCard", "label": "GiftCard"},
                                  {"component": "FormCard", "form": "ui_form_gift_card"}]


def test_gift_card_form_alone_when_no_list_is_offered():
    schema = build_schema(CANDIDATE_DICTS, forms=("ui_form_gift_card",))
    selection = select(schema, CANDIDATE_DICTS, "do you sell gift cards?")
    assert selection["views"] == [{"component": "FormCard", "form": "ui_form_gift_card"}]


def test_fact_card_by_name():
    schema = build_schema(CANDIDATE_DICTS, forms=(), labels=("GiftCard",))
    selection = select(schema, CANDIDATE_DICTS, "tell me about the standard gift card")
    assert selection["views"][0] in ({"component": "FactCard", "node": "gc_standard"},
                                     {"component": "ListCard", "label": "GiftCard"})


@pytest.mark.parametrize(
    ("text", "expected"),
    [("is there parking nearby?", {"kind": "gap", "topic": "parking"}),
     ("vegetarian options", {"kind": "gap", "topic": "vegetarian"}),
     ("tell me a joke", {"kind": "off_topic"}),
     ("what is the capital of France", {"kind": "off_topic"}),
     ("???", {"kind": "off_topic"})],
)
def test_zero_candidates_offers_only_gap_and_off_topic(text, expected):
    schema = build_schema([])
    selection = select(schema, [], text)
    jsonschema.validate(selection, schema)
    assert selection == expected


def test_never_names_an_id_the_schema_does_not_offer():
    few = [c for c in CANDIDATE_DICTS if c["id"] in ("sec_burgers", "faq_brunch")]
    schema = build_schema(few, forms=())
    extra = [*few, {"id": "mi_guinness", "label": "MenuItem", "name": "Guinness", "facts": ""}]
    for text, _ in EXPECTED:
        selection = select(schema, extra, text)
        jsonschema.validate(selection, schema)
    assert select(schema, extra, "do you have Guinness?") == {"kind": "gap", "topic": "guinness"}


def test_gluten_free_is_a_diet_not_an_allergen():
    selection = select(SCHEMA, CANDIDATE_DICTS, "anything gluten-free?")
    assert selection == _menu(diet="diet_gluten_free")


def test_allergy_with_unknown_allergen_takes_the_first_offered():
    selection = select(SCHEMA, CANDIDATE_DICTS, "my son has a kiwi allergy")
    assert selection == _one("AllergenNotice", allergen="alg_tree_nuts")


def test_item_named_only_by_a_generic_word_is_not_picked():
    assert select(SCHEMA, CANDIDATE_DICTS, "what is the kenmore?") == _one(
        "Answer", faq="faq_about")
    assert select(SCHEMA, CANDIDATE_DICTS, "the kenmore burger please") == _menu(
        items=["mi_the_kenmore_burger"])


def test_diet_and_section_combine():
    assert select(SCHEMA, CANDIDATE_DICTS, "vegetarian burgers") == _menu(
        diet="diet_vegetarian", section="sec_burgers")


def test_ordering_words_set_order():
    assert select(SCHEMA, CANDIDATE_DICTS, "a Guinness to go") == _menu(
        items=["mi_guinness"], order=True)


def test_gap_topic_is_capped_at_sixty_characters():
    text = "do you validate " + "extraordinarily " * 6 + "parking tickets"
    selection = select(SCHEMA, CANDIDATE_DICTS, text)
    assert selection["kind"] == "gap"
    assert 0 < len(selection["topic"]) <= 60


def test_invalid_pick_falls_back_to_off_topic():
    schema = {"anyOf": [_OFF]}
    assert select(schema, [], "is there parking nearby?") == {"kind": "off_topic"}


def test_single_variant_schema_without_anyof_is_understood():
    views = _variant(["component"], {"component": {"enum": ["HoursCard"]}})
    answer = _variant(["kind", "views"], {
        "kind": {"const": "answer"},
        "views": {"type": "array", "minItems": 1, "maxItems": 2, "items": views}})
    schema = {"anyOf": [answer, _GAP, _OFF]}
    assert parse_offer(schema).components == {"HoursCard"}
    assert select(schema, [], "are you open tonight?") == _one("HoursCard")


def test_deterministic():
    first = [select(SCHEMA, CANDIDATE_DICTS, text) for text, _ in EXPECTED]
    second = [select(SCHEMA, CANDIDATE_DICTS, text) for text, _ in EXPECTED]
    assert first == second
