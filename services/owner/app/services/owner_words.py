"""The owner's own words: an answer to a gap, and special hours (SCHEMA 8.6).

These are the one place an agent call produces verified content, because the text is the
owner's: the owner channel accepts messages only from OWNER_CHANNEL_USER_ID.
"""

import re
from datetime import date

import psycopg
from cac_common.graph import reindex_node
from cac_common.settings import Settings
from psycopg.types.json import Jsonb

from app.domain.requests import ChangeError, ChangeRequest
from app.domain.tiers import Kind, TierDecision
from app.infra import graph
from app.services import topics
from app.services.change_engine import Plan, record_change

CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
OWNER_DECISION = TierDecision("auto", Kind.NEW_PUBLIC_NODE, "the owner's own words")


def luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def has_card_or_ssn(text: str) -> bool:
    """Card numbers and SSNs are never stored anywhere in CAC (PRD section 10, invariant 7)."""
    if SSN_RE.search(text):
        return True
    return any(luhn(re.sub(r"\D", "", m.group())) for m in CARD_RE.finditer(text))


def _business_node(conn: psycopg.Connection, biz: str) -> str | None:
    row = conn.execute("SELECT id FROM kg.node WHERE business_id = %s AND label = 'Business'"
                       " ORDER BY id LIMIT 1", (biz,)).fetchone()
    return row["id"] if row else None


def _owner_edge(conn: psycopg.Connection, biz: str, key: tuple[str, str, str]) -> None:
    """Insert an approved, owner-verified edge, if the edge type exists in the registry."""
    src, dst, edge_type = key
    if graph.get_edge_type(conn, edge_type) is None:
        return
    conn.execute(
        "INSERT INTO kg.edge (business_id, src, dst, type, status, source_type,"
        " verified_by_owner, verified_at) VALUES (%s, %s, %s, %s, 'approved', 'owner', true,"
        " now()) ON CONFLICT (src, dst, type) DO UPDATE SET status = 'approved',"
        " verified_by_owner = true, verified_at = now()", (biz, src, dst, edge_type))


def _owner_node(conn: psycopg.Connection, biz: str, node: dict) -> None:
    conn.execute(
        "INSERT INTO kg.node (id, business_id, label, name, props, visibility, status,"
        " source_type, extracted_by, verified_by_owner, verified_at) VALUES"
        " (%s, %s, %s, %s, %s, 'public', 'approved', 'owner', 'owner', true, now())"
        " ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, props = EXCLUDED.props,"
        " status = 'approved', source_type = 'owner', verified_by_owner = true,"
        " verified_at = now(), updated_at = now()",
        (node["id"], biz, node["label"], node["name"], Jsonb(node["props"])))


def _free_faq_id(conn: psycopg.Connection, topic: str) -> str:
    base, n = f"faq_{topics.slug(topic)}", 1
    while graph.get_node(conn, base if n == 1 else f"{base}_{n}"):
        n += 1
    return base if n == 1 else f"{base}_{n}"


def _record(conn: psycopg.Connection, biz: str, request: ChangeRequest, before: dict | None,
            action: str) -> None:
    plan = Plan(request.target, before, OWNER_DECISION, actor="owner")
    record_change(conn, biz, request.model_copy(update={"action": action}), plan, "applied")


def answer(conn: psycopg.Connection, settings: Settings, gap_id: str, text: str) -> dict:
    """Turn the owner's reply into a verified, approved, public FAQ in their exact words."""
    biz = settings.business_id
    gap = topics.load_gap(conn, settings, gap_id)
    if gap["props"]["state"] != "asked":
        raise ChangeError(409, f"gap {gap_id} is {gap['props']['state']}, not asked")
    topic = gap["props"]["topic"]
    faq_id = _free_faq_id(conn, topic)
    props = {"question": f"What about {topic}?", "answer": text}
    node = {"id": faq_id, "label": "FAQ", "name": props["question"], "props": props}
    _owner_node(conn, biz, node)
    reindex_node(conn, faq_id)
    business = _business_node(conn, biz)
    if business:
        _owner_edge(conn, biz, (faq_id, business, "ANSWERS"))
    _owner_edge(conn, biz, (gap_id, faq_id, "ABOUT"))
    topics.set_gap_state(conn, gap, "answered", answered_with=faq_id)
    request = ChangeRequest(
        action="create_node", target=faq_id,
        after={"label": "FAQ", "name": node["name"], "props": props},
        reason=f"The owner's answer to what visitors asked about {topic}",
        evidence={"topic": topic, "count": gap["props"].get("count"), "gap_id": gap_id})
    _record(conn, biz, request, None, "create_node")
    return {"faq": faq_id, "gap_id": gap_id, "state": "answered", "verified": True}


def special_hours(conn: psycopg.Connection, settings: Settings, fields: dict) -> dict:
    """Create or update an owner-verified SpecialHours node from an owner message."""
    biz = settings.business_id
    day = date.fromisoformat(fields["date"])
    node_id = f"sh_{day.year}_{day.month:02d}_{day.day:02d}"
    existing = graph.get_node(conn, node_id)
    props = {k: v for k, v in fields.items() if v is not None}
    node = {"id": node_id, "label": "SpecialHours", "name": f"Special hours {fields['date']}",
            "props": props}
    _owner_node(conn, biz, node)
    reindex_node(conn, node_id)
    business = _business_node(conn, biz)
    if business:
        _owner_edge(conn, biz, (business, node_id, "HAS_HOURS"))
    before = None if existing is None else {k: existing[k] for k in ("name", "props",
                                                                    "visibility", "status")}
    request = ChangeRequest(
        action="create_node" if existing is None else "update_node", target=node_id,
        after={"label": "SpecialHours", "name": node["name"], "props": props},
        reason=f"The owner set special hours for {fields['date']}", evidence={})
    _record(conn, biz, request, before, request.action)
    return {"node_id": node_id, "verified": True}
