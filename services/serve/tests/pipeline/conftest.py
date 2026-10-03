"""A hand-built graph that mirrors the SCHEMA 8.1 example, for the pure pipeline tests."""

from __future__ import annotations

import pytest

from cac_serve.domain.graph import Edge, Graph, Node


def _catalog(component: str, use_when: str, **extra) -> Node:
    node_id = extra.pop("id", None) or "ui_" + component.lower()
    props = {"component": component, "version": 1, "use_when": use_when,
             "selectable": True, "primitive": None, **extra}
    return Node(node_id, "UIComponent", component, props)


CATALOG = [
    _catalog("Answer", "A stored FAQ answers the question.", id="ui_answer"),
    _catalog("MenuList", "Food or drinks, a diet, or a named item.", id="ui_menu_list"),
    _catalog("HoursCard", "Opening hours.", id="ui_hours_card"),
    _catalog("BookingForm", "Visitor wants a table.", id="ui_booking_form"),
    _catalog("CateringQuoteForm", "Catering or a large group.", id="ui_catering_quote_form"),
    _catalog("AllergenNotice", "Visitor names an allergen.", id="ui_allergen_notice"),
    _catalog("GoalCTA", "Never selected.", id="ui_goal_cta", selectable=False),
    _catalog("FactCard", "One node of a label with no component.", id="ui_fact_card"),
    _catalog("ListCard", "Several nodes of one such label.", id="ui_list_card"),
    _catalog("FormCard", "Visitor wants to buy a gift card.", id="ui_form_gift_card",
             primitive="FormCard", fields=[{"name": "amount", "type": "number"}]),
]

DATA = [
    Node("biz_x", "Business", "Trattoria", {"phone": "+1 555 0100"}),
    Node("diet_vegetarian", "Diet", "Vegetarian", {"synonyms": ["veggie", "meatless"]}),
    Node("diet_vegan", "Diet", "Vegan", {"synonyms": ["plant based"]}),
    Node("sec_mains", "MenuSection", "Mains", {"position": 1}),
    Node("sec_desserts", "MenuSection", "Desserts", {"position": 2}),
    Node("mi_mushroom_risotto", "MenuItem", "Mushroom risotto",
         {"description": "Arborio rice | porcini\nand parmesan", "price_cents": 1850,
          "currency": "USD", "available": True}),
    Node("mi_caprese", "MenuItem", "Caprese", {"description": "Tomato, mozzarella",
                                               "price_cents": 1200}),
    Node("mi_ribeye", "MenuItem", "Ribeye", {"description": "x" * 300, "price_cents": 4200}),
    Node("faq_parking", "FAQ", "Is there parking?",
         {"question": "Is there parking?", "answer": "Street parking only."}),
    Node("faq_gluten_free_pasta", "FAQ", "Do you have gluten-free pasta?",
         {"question": "Do you have gluten-free pasta?", "answer": "Yes."}),
    Node("alg_peanuts", "Allergen", "Peanuts", {"fda_major": True, "synonyms": ["peanut"]}),
    Node("hrs_all", "HoursSpec", "Every day", {"days": ["mon"], "opens": "11:00",
                                               "closes": "22:00"}),
    Node("sh_2026_11_26", "SpecialHours", "Thanksgiving",
         {"date": "2026-11-26", "closed": True, "note": "Thanksgiving"}),
    Node("svc_reservations", "Service", "Table requests", {"kind": "reservations"}),
    Node("svc_catering", "Service", "Catering", {"kind": "catering"}),
    Node("svc_private_events", "Service", "Private events", {"kind": "private_events"}),
    Node("gc_standard", "GiftCard", "Standard gift card", {"amounts": [25, 50], "terms": "x"}),
    Node("trait_color", "BrandTrait", "Background", {"kind": "color", "value": "#111"}),
]

EDGES = [
    Edge("sec_mains", "mi_mushroom_risotto", "HAS_ITEM"),
    Edge("sec_mains", "mi_ribeye", "HAS_ITEM"),
    Edge("sec_desserts", "mi_caprese", "HAS_ITEM"),
    Edge("mi_mushroom_risotto", "diet_vegetarian", "SUITABLE_FOR", verified=True),
    Edge("mi_caprese", "diet_vegetarian", "SUITABLE_FOR"),
    Edge("mi_ribeye", "alg_peanuts", "CONTAINS_ALLERGEN"),
    Edge("mi_caprese", "alg_peanuts", "CONTAINS_ALLERGEN", verified=True),
    Edge("faq_parking", "biz_x", "ANSWERS"),
    Edge("faq_gluten_free_pasta", "svc_private_events", "ANSWERS"),
    Edge("biz_x", "gc_standard", "SELLS"),
    Edge("gc_standard", "trait_color", "STYLED_BY"),
    Edge("gc_standard", "ui_form_gift_card", "SOLD_WITH"),
    Edge("gc_standard", "ui_menu_list", "SHOWN_IN"),
]

EXAMPLE_CANDIDATES = [
    "diet_vegetarian", "diet_vegan", "sec_mains", "sec_desserts",
    "mi_mushroom_risotto", "mi_caprese", "mi_ribeye",
    "faq_parking", "faq_gluten_free_pasta", "alg_peanuts",
    "gc_standard", "svc_private_events",
]


@pytest.fixture()
def example_graph() -> Graph:
    return Graph("biz_x", 1, [*DATA, *CATALOG], EDGES)


@pytest.fixture()
def example_candidates() -> list[str]:
    return list(EXAMPLE_CANDIDATES)
