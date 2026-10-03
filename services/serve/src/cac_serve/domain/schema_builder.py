"""The per-request selection schema (SCHEMA 8.1).

Built from the approved catalog and this request's candidates, so the model can only name
components that are approved and ids that were retrieved. Nothing is cached: a label or a
form the agent added is selectable on the first request after publish.
"""

from __future__ import annotations

from cac_serve.domain.graph import Graph, Node

MAX_VIEWS = 2
MAX_NAMED_ITEMS = 6
MAX_TOPIC_CHARS = 60
HOURS_LABELS = ("HoursSpec", "SpecialHours")
# Labels with a purpose-built component; every other label is FactCard and ListCard material.
PURPOSE_BUILT = frozenset(
    {"MenuItem", "MenuSection", "Diet", "Allergen", "FAQ", "UIComponent", *HOURS_LABELS}
)
FORM_SERVICE_KINDS = {"reservations": "BookingForm", "catering": "CateringQuoteForm"}
# A Service is only partly generic (two kinds have forms), so it is never offered as a list.
_NO_LIST_LABELS = frozenset({"Service"})


def _variant(required: list[str], properties: dict) -> dict:
    return {"type": "object", "additionalProperties": False, "required": required,
            "properties": properties}


def _offered(graph: Graph, component: str) -> bool:
    entry = graph.component(component)
    return entry is not None and bool(entry.props.get("selectable"))


def _ids(nodes: list[Node], label: str) -> list[str]:
    return [n.id for n in nodes if n.label == label]


def is_generic(node: Node) -> bool:
    """True when no purpose-built component covers the node (FactCard and ListCard material)."""
    if node.label == "Service":
        return node.props.get("kind") not in FORM_SERVICE_KINDS
    return node.label not in PURPOSE_BUILT and node.label != "BrandTrait"


def _menu_list(graph: Graph, nodes: list[Node]) -> dict | None:
    diets, sections, items = (_ids(nodes, label) for label in ("Diet", "MenuSection", "MenuItem"))
    if not (diets or sections or items) or not _offered(graph, "MenuList"):
        return None
    named: dict = {"type": "array", "maxItems": 0}
    if items:
        named = {"type": "array", "maxItems": MAX_NAMED_ITEMS, "items": {"enum": items}}
    return _variant(["component", "diet", "section", "items", "order"], {
        "component": {"const": "MenuList"},
        "diet": {"enum": [*diets, None]},
        "section": {"enum": [*sections, None]},
        "items": named,
        "order": {"type": "boolean"},
    })


def _by_id(graph: Graph, nodes: list[Node], component: str, key: str, label: str) -> dict | None:
    ids = _ids(nodes, label)
    if not ids or not _offered(graph, component):
        return None
    return _variant(["component", key], {"component": {"const": component}, key: {"enum": ids}})


def _no_id(graph: Graph) -> dict | None:
    kinds = {n.props.get("kind") for n in graph.by_label("Service")}
    eligible = {
        "HoursCard": any(graph.by_label(label) for label in HOURS_LABELS),
        "BookingForm": "reservations" in kinds,
        "CateringQuoteForm": "catering" in kinds,
    }
    names = [name for name, ok in eligible.items() if ok and _offered(graph, name)]
    return _variant(["component"], {"component": {"enum": names}}) if names else None


def _generic(graph: Graph, nodes: list[Node]) -> list[dict | None]:
    generic = [n for n in nodes if is_generic(n)]
    labels = list(dict.fromkeys(n.label for n in generic if n.label not in _NO_LIST_LABELS))
    fact = card = None
    if generic and _offered(graph, "FactCard"):
        fact = _variant(["component", "node"], {
            "component": {"const": "FactCard"}, "node": {"enum": [n.id for n in generic]}})
    if labels and _offered(graph, "ListCard"):
        card = _variant(["component", "label"], {
            "component": {"const": "ListCard"}, "label": {"enum": labels}})
    return [fact, card]


def _form_card(graph: Graph) -> dict | None:
    forms = [n.id for n in graph.forms() if n.props.get("selectable")]
    if not forms:
        return None
    return _variant(["component", "form"], {
        "component": {"const": "FormCard"}, "form": {"enum": forms}})


def _view_variants(graph: Graph, nodes: list[Node]) -> list[dict]:
    variants = [
        _menu_list(graph, nodes),
        _by_id(graph, nodes, "Answer", "faq", "FAQ"),
        _by_id(graph, nodes, "AllergenNotice", "allergen", "Allergen"),
        _no_id(graph),
        *_generic(graph, nodes),
        _form_card(graph),
    ]
    return [v for v in variants if v is not None]


def _gap() -> dict:
    return _variant(["kind", "topic"], {
        "kind": {"const": "gap"}, "topic": {"type": "string", "maxLength": MAX_TOPIC_CHARS}})


def _off_topic() -> dict:
    return _variant(["kind"], {"kind": {"const": "off_topic"}})


def build_schema(graph: Graph, candidate_ids: list[str]) -> dict:
    """The JSON Schema one model call is constrained to. Never contains an empty enum."""
    nodes = [n for n in map(graph.get, dict.fromkeys(candidate_ids)) if n is not None]
    views = _view_variants(graph, nodes) if nodes else []
    if not views:
        return {"anyOf": [_gap(), _off_topic()]}
    answer = _variant(["kind", "views"], {
        "kind": {"const": "answer"},
        "views": {"type": "array", "minItems": 1, "maxItems": MAX_VIEWS,
                  "items": {"anyOf": views}},
    })
    return {"anyOf": [answer, _gap(), _off_topic()]}
