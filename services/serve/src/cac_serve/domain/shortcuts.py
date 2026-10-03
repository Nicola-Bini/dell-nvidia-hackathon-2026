"""Texts that open a preset with no model call (SCHEMA section 7, presets).

The widget sends a clicked chip as intent text. A chip that is a goal button's label
("Book a table"), a navigation label ("Menu") or a whole-menu ask ("See the menu") is a
click on a fixed surface, so code routes it: the model is not asked.
"""

from __future__ import annotations

import re

from cac_serve.domain.graph import Graph
from cac_serve.domain.normalize import normalize

_WHOLE_MENU = re.compile(
    r"^(?:(?:can|could|may) i )?(?:please )?(?:see|show|view|open|whats on|what is on)? ?"
    r"(?:me )?(?:the |your )?(?:full |whole |entire )?menu(?: please)?$"
)


def _labels(graph: Graph) -> dict[str, str]:
    """Normalized label -> preset id, from goal button labels and the bootstrap nav."""
    labels: dict[str, str] = {}
    business = graph.business()
    for entry in (business.props.get("nav") if business is not None else None) or []:
        if isinstance(entry, dict) and entry.get("label") and entry.get("preset"):
            labels[normalize(str(entry["label"]))] = str(entry["preset"])
    for node in graph.catalog():
        label, preset = node.props.get("cta_label"), node.props.get("preset")
        if label and preset:
            labels[normalize(str(label))] = str(preset)
    return labels


def preset_for(graph: Graph, text: str) -> str | None:
    """The preset this text opens, or None when it is a real question for the pipeline."""
    key = normalize(text)
    if _WHOLE_MENU.match(key):
        return "menu"
    return _labels(graph).get(key)
