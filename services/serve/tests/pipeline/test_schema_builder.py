"""SCHEMA 8.1: the per-request JSON Schema, built from the catalog and the candidates."""

from __future__ import annotations

import jsonschema
import pytest

from cac_serve.domain.graph import Node
from cac_serve.domain.schema_builder import build_schema

GAP = {
    "type": "object", "additionalProperties": False, "required": ["kind", "topic"],
    "properties": {"kind": {"const": "gap"}, "topic": {"type": "string", "maxLength": 60}},
}
OFF_TOPIC = {
    "type": "object", "additionalProperties": False, "required": ["kind"],
    "properties": {"kind": {"const": "off_topic"}},
}


def _variant(required: list[str], properties: dict) -> dict:
    return {"type": "object", "additionalProperties": False, "required": required,
            "properties": properties}


# The SCHEMA 8.1 example, key for key.
EXAMPLE = {
    "anyOf": [
        _variant(["kind", "views"], {
            "kind": {"const": "answer"},
            "views": {
                "type": "array", "minItems": 1, "maxItems": 2,
                "items": {"anyOf": [
                    _variant(["component", "diet", "section", "items", "order"], {
                        "component": {"const": "MenuList"},
                        "diet": {"enum": ["diet_vegetarian", "diet_vegan", None]},
                        "section": {"enum": ["sec_mains", "sec_desserts", None]},
                        "items": {
                            "type": "array", "maxItems": 6,
                            "items": {"enum": ["mi_mushroom_risotto", "mi_caprese", "mi_ribeye"]},
                        },
                        "order": {"type": "boolean"},
                    }),
                    _variant(["component", "faq"], {
                        "component": {"const": "Answer"},
                        "faq": {"enum": ["faq_parking", "faq_gluten_free_pasta"]},
                    }),
                    _variant(["component", "allergen"], {
                        "component": {"const": "AllergenNotice"},
                        "allergen": {"enum": ["alg_peanuts"]},
                    }),
                    _variant(["component"], {
                        "component": {"enum": ["HoursCard", "BookingForm", "CateringQuoteForm"]},
                    }),
                    _variant(["component", "node"], {
                        "component": {"const": "FactCard"},
                        "node": {"enum": ["gc_standard", "svc_private_events"]},
                    }),
                    _variant(["component", "label"], {
                        "component": {"const": "ListCard"},
                        "label": {"enum": ["GiftCard"]},
                    }),
                    _variant(["component", "form"], {
                        "component": {"const": "FormCard"},
                        "form": {"enum": ["ui_form_gift_card"]},
                    }),
                ]},
            },
        }),
        GAP,
        OFF_TOPIC,
    ]
}


def _views(schema: dict) -> list[dict]:
    return schema["anyOf"][0]["properties"]["views"]["items"]["anyOf"]


def _by_component(schema: dict) -> dict[str, dict]:
    out = {}
    for variant in _views(schema):
        component = variant["properties"]["component"]
        out[component.get("const", "no_id")] = variant
    return out


def _enums(value) -> list[list]:
    if isinstance(value, dict):
        found = [value["enum"]] if "enum" in value else []
        return found + [e for v in value.values() for e in _enums(v)]
    if isinstance(value, list):
        return [e for v in value for e in _enums(v)]
    return []


def test_reproduces_the_schema_8_1_example(example_graph, example_candidates):
    assert build_schema(example_graph, example_candidates) == EXAMPLE


def test_example_selections_validate(example_graph, example_candidates):
    schema = build_schema(example_graph, example_candidates)
    jsonschema.Draft202012Validator.check_schema(schema)
    good = [
        {"kind": "answer", "views": [{"component": "MenuList", "diet": "diet_vegetarian",
                                      "section": None, "items": [], "order": False}]},
        {"kind": "answer", "views": [{"component": "HoursCard"}]},
        {"kind": "answer", "views": [{"component": "AllergenNotice", "allergen": "alg_peanuts"}]},
        {"kind": "answer", "views": [{"component": "ListCard", "label": "GiftCard"},
                                     {"component": "FormCard", "form": "ui_form_gift_card"}]},
        {"kind": "gap", "topic": "gluten-free pasta"},
        {"kind": "off_topic"},
    ]
    for selection in good:
        jsonschema.validate(selection, schema)
    bad = [
        {"kind": "answer", "views": []},
        {"kind": "answer", "views": [{"component": "GoalCTA"}]},
        {"kind": "answer", "views": [{"component": "Answer", "faq": "faq_made_up"}]},
        {"kind": "answer", "views": [{"component": "HoursCard"}] * 3},
        {"kind": "gap", "topic": "x" * 61},
        {"kind": "off_topic", "say": "a joke"},
    ]
    for selection in bad:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(selection, schema)


def test_zero_candidates_offers_only_gap_and_off_topic(example_graph):
    assert build_schema(example_graph, []) == {"anyOf": [GAP, OFF_TOPIC]}


def test_unknown_candidate_ids_count_as_no_candidates(example_graph):
    assert build_schema(example_graph, ["mi_not_published"]) == {"anyOf": [GAP, OFF_TOPIC]}


@pytest.mark.parametrize(
    "candidates",
    [["faq_parking"], ["diet_vegan"], ["sec_mains"], ["alg_peanuts"], ["gc_standard"],
     ["hrs_all"], ["svc_reservations"], ["mi_caprese"], ["ui_form_gift_card"]],
)
def test_never_emits_an_empty_enum(example_graph, candidates):
    schema = build_schema(example_graph, candidates)
    jsonschema.Draft202012Validator.check_schema(schema)
    assert all(len(enum) > 0 for enum in _enums(schema))


def test_faq_only_omits_the_variants_with_no_candidates(example_graph):
    variants = _by_component(build_schema(example_graph, ["faq_parking"]))
    assert list(variants) == ["Answer", "no_id", "FormCard"]
    assert variants["Answer"]["properties"]["faq"] == {"enum": ["faq_parking"]}


def test_menu_list_with_a_diet_but_no_items(example_graph):
    menu = _by_component(build_schema(example_graph, ["diet_vegan"]))["MenuList"]
    assert menu["properties"]["diet"] == {"enum": ["diet_vegan", None]}
    assert menu["properties"]["section"] == {"enum": [None]}
    assert menu["properties"]["items"] == {"type": "array", "maxItems": 0}


def test_form_covered_services_are_not_fact_cards(example_graph):
    variants = _by_component(build_schema(example_graph, ["svc_reservations", "svc_catering"]))
    assert "FactCard" not in variants
    assert "ListCard" not in variants


def test_no_id_variant_follows_the_graph(example_graph):
    kept = [n for n in example_graph.nodes.values()
            if n.label not in ("HoursSpec", "SpecialHours") and n.id != "svc_catering"]
    graph = type(example_graph)("biz_x", 1, kept, [])
    no_id = _by_component(build_schema(graph, ["faq_parking"]))["no_id"]
    assert no_id["properties"]["component"] == {"enum": ["BookingForm"]}


def test_unselectable_or_missing_entries_are_not_offered(example_graph):
    off = Node("ui_answer", "UIComponent", "Answer",
               {"component": "Answer", "use_when": "x", "selectable": False})
    graph = example_graph.extended([off])
    assert "Answer" not in _by_component(build_schema(graph, ["faq_parking"]))


def test_a_form_added_after_publish_is_selectable_at_once(example_graph):
    form = Node("ui_form_private_dining", "UIComponent", "FormCard",
                {"component": "FormCard", "primitive": "FormCard", "use_when": "x",
                 "selectable": True, "fields": []})
    graph = example_graph.extended([form])
    card = _by_component(build_schema(graph, ["faq_parking"]))["FormCard"]
    assert card["properties"]["form"] == {
        "enum": ["ui_form_gift_card", "ui_form_private_dining"]}
