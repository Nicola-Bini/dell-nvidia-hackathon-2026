"""Retrieval (SCHEMA section 6): entry nodes, then fixed expansion templates, capped at 40.

The model never writes a query. Entry nodes come from the embedder when there is one and
from Postgres full-text search otherwise; slots add entries in code; each entry label has
one fixed expansion over the request's graph snapshot.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from cac_serve.domain.graph import Graph, Node
from cac_serve.domain.normalize import normalize
from cac_serve.infra import search_repo

ENTRY_LIMIT = 8
CANDIDATE_CAP = 40
SIMILARITY_THRESHOLD = 0.35
HOURS_LABELS = ("HoursSpec", "SpecialHours")
SLOT_SERVICE_KINDS = {"party_size": "reservations", "headcount": "catering"}

# Words that carry no retrieval signal in a visitor's question.
STOPWORDS = frozenset({
    "a", "about", "also", "am", "an", "and", "any", "anything", "are", "as", "at", "available",
    "be", "been", "by", "can", "could", "d", "do", "does", "for", "free", "from", "get", "give",
    "got", "had", "has", "have", "having", "hello", "here", "hey", "hi", "how", "i", "id", "if",
    "im", "in", "is", "it", "its", "ive", "just", "kind", "know", "let", "like", "ll", "looking",
    "many", "may", "me", "might", "much", "my", "need", "no", "not", "now", "of", "offer",
    "offers", "on", "or", "our", "out", "please", "s", "serve", "serves", "should", "show", "so",
    "some", "something", "sort", "t", "tell", "than", "thank", "thanks", "that", "the", "their",
    "them", "then", "there", "these", "they", "this", "those", "time", "to", "too", "type",
    "types", "up", "us", "want", "was", "we", "were", "what", "whats", "when", "where", "which",
    "who", "whom", "why", "will", "with", "would", "you", "your",
})
# "40", "4th", "7pm": slot material, already read by code.
_COUNT_OR_TIME = re.compile(r"\d+(?:am|pm|st|nd|rd|th)?$")
# Questions about opening times name no node, so these words bring in the hours nodes.
HOURS_WORDS = frozenset({"open", "opens", "opening", "close", "closes", "closed", "closing",
                         "hours"})


def query_tokens(text: str) -> list[str]:
    """The normalized words of the text that are worth searching for, in order."""
    tokens = [t for t in normalize(text).split()
              if t not in STOPWORDS and len(t) > 1 and not _COUNT_OR_TIME.match(t)]
    return list(dict.fromkeys(tokens))


def _embedding(text: str) -> list[float] | None:
    """The query vector, or None when there is no embedder (or it is not answering)."""
    try:
        from cac_common.embedding import embed
    except ImportError:
        return None
    try:
        vectors = embed([text])
    except Exception:  # noqa: BLE001 - a failing embedder must degrade to full-text search
        return None
    return vectors[0] if vectors else None


def _searched(conn, graph: Graph, text: str) -> list[str]:
    vector = _embedding(text)
    if vector:
        found = search_repo.vector_entries(conn, graph.business_id, vector, ENTRY_LIMIT,
                                           SIMILARITY_THRESHOLD)
        if found:
            return found
    return search_repo.text_entries(conn, graph.business_id, query_tokens(text), ENTRY_LIMIT)


def _hours(graph: Graph) -> list[str]:
    return [n.id for label in HOURS_LABELS for n in graph.by_label(label)]


def _slot_entries(graph: Graph, text: str, slots: dict) -> list[str]:
    """Entries decided by code: a date or time means hours, a head count means a service."""
    ids: list[str] = []
    if "date" in slots or "time" in slots or HOURS_WORDS & set(normalize(text).split()):
        ids += _hours(graph)
    for slot, kind in SLOT_SERVICE_KINDS.items():
        if slot in slots:
            ids += [n.id for n in graph.by_label("Service") if n.props.get("kind") == kind]
    return ids


def _is_form(node: Node) -> bool:
    return node.label == "UIComponent" and node.props.get("primitive") == "FormCard"


def _allowed(node: Node | None) -> bool:
    """Candidates are data nodes and configured forms; never other catalog entries or brand."""
    if node is None or node.label == "BrandTrait":
        return False
    return node.label != "UIComponent" or _is_form(node)


def _sections_of(graph: Graph, item_ids: Iterable[str]) -> list[str]:
    return [e.src for item in item_ids for e in graph.in_edges(item, "HAS_ITEM")]


def _expand_diet(graph: Graph, node: Node) -> list[str]:
    edges = sorted(graph.in_edges(node.id, "SUITABLE_FOR"), key=lambda e: not e.verified)
    items = [e.src for e in edges]
    return items + _sections_of(graph, items)


def _expand_allergen(graph: Graph, node: Node) -> list[str]:
    return [e.src for e in graph.in_edges(node.id, "CONTAINS_ALLERGEN") if e.verified]


def _expand_item(graph: Graph, node: Node) -> list[str]:
    diets = [e.dst for e in graph.out_edges(node.id, "SUITABLE_FOR")]
    allergens = [e.dst for e in graph.out_edges(node.id, "CONTAINS_ALLERGEN") if e.verified]
    return _sections_of(graph, [node.id]) + diets + allergens


def _expand_section(graph: Graph, node: Node) -> list[str]:
    edges = sorted(graph.out_edges(node.id, "HAS_ITEM"),
                   key=lambda e: e.props.get("position") or 0)
    return [e.dst for e in edges]


def _expand_service(graph: Graph, node: Node) -> list[str]:
    return [e.src for e in graph.in_edges(node.id, "ANSWERS")]


def _expand_hours(graph: Graph, node: Node) -> list[str]:
    return _hours(graph)


def _expand_self(graph: Graph, node: Node) -> list[str]:
    return []


def _expand_one_hop(graph: Graph, node: Node) -> list[str]:
    return [e.dst for e in graph.out_edges(node.id)] + [e.src for e in graph.in_edges(node.id)]


_EXPANSIONS: dict[str, Callable[[Graph, Node], list[str]]] = {
    "Diet": _expand_diet,
    "Allergen": _expand_allergen,
    "MenuItem": _expand_item,
    "MenuSection": _expand_section,
    "Service": _expand_service,
    "HoursSpec": _expand_hours,
    "SpecialHours": _expand_hours,
    "FAQ": _expand_self,
    "UIComponent": _expand_self,
}


def expand(graph: Graph, node_id: str) -> list[str]:
    """The fixed expansion for one entry node; labels with no template get one hop."""
    node = graph.get(node_id)
    if node is None:
        return []
    return _EXPANSIONS.get(node.label, _expand_one_hop)(graph, node)


def candidates_from(graph: Graph, entry_ids: Iterable[str]) -> list[str]:
    """Entries in rank order, then their expansions; de-duplicated, filtered, capped."""
    entries = [i for i in dict.fromkeys(entry_ids) if _allowed(graph.get(i))]
    expanded = [i for entry in entries for i in expand(graph, entry)]
    ordered = dict.fromkeys([*entries, *(i for i in expanded if _allowed(graph.get(i)))])
    return list(ordered)[:CANDIDATE_CAP]


def retrieve(conn, graph: Graph, text: str, slots: dict) -> list[str]:
    """Ordered candidate node ids for one visitor text, at most 40."""
    entries = [*_searched(conn, graph, text), *_slot_entries(graph, text, slots)]
    return candidates_from(graph, entries)
