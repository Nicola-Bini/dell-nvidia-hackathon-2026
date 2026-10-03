"""Helpers shared by the binder tests: golden loaders and selection builders."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from cac_serve.domain.graph import Graph, Node

# The root conftest is loaded by path: several test folders have their own `conftest`
# module, so a plain `import conftest` would be ambiguous.
_spec = importlib.util.spec_from_file_location(
    "cac_serve_tests_conftest", Path(__file__).resolve().parents[1] / "conftest.py"
)
_root = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root)

load_golden = _root.load_golden
strip_volatile = _root.strip_volatile
TODAY = _root.TODAY

GIFT_TERMS = "Valid for 12 months. Redeemable in the bar."


def answer(*views: dict) -> dict:
    return {"kind": "answer", "views": list(views)}


def menu(diet=None, section=None, items=(), order=False) -> dict:
    return {"component": "MenuList", "diet": diet, "section": section, "items": list(items),
            "order": order}


def view(component: str, **ids) -> dict:
    return {"component": component, **ids}


def components(surface: dict) -> list[str]:
    return [v["component"] for v in surface["views"]]


def first(surface: dict, component: str) -> dict:
    return next(v for v in surface["views"] if v["component"] == component)


def gift_card_graph(graph: Graph) -> Graph:
    """The graph after the agent added a GiftCard label, two nodes and a request form."""
    form = load_golden("gift_cards")["views"][1]["data"]
    entry = Node(
        id="ui_form_gift_card", label="UIComponent", name="Gift card request",
        props={
            "component": "FormCard", "primitive": "FormCard", "version": 1,
            "use_when": "Visitor wants to buy a gift card.",
            "binds": {"labels": ["Service"], "min": 0, "max": 1}, "selectable": True,
            "rail_label": "Gift card", "title": form["title"], "say": None,
            "chips": ["See the menu"], "channels": ["web", "mcp"],
            "fields": form["fields"], "submit_label": form["submit_label"],
        },
    )
    cards = [
        Node(id=f"gc_{amount}", label="GiftCard", name=f"${amount} gift card",
             props={"amounts": [f"${amount}"], "terms": GIFT_TERMS})
        for amount in (25, 50)
    ]
    return graph.extended([*cards, entry])
