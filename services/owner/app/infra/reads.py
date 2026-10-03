"""Read-side SQL for the agent endpoints. Locked labels never leave these queries."""

from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg

from app.domain.tiers import LOCKED_LABELS

LOCKED_LOWER = [x.lower() for x in LOCKED_LABELS]
# A node is readable by the agent when its label is neither flagged locked nor a reserved name.
READABLE = "l.locked = false AND lower(n.label) <> ALL (%(locked)s)"


def is_locked_label(conn: psycopg.Connection, label: str) -> bool:
    if label.lower() in LOCKED_LOWER:
        return True
    row = conn.execute("SELECT locked FROM kg.label WHERE label = %s", (label,)).fetchone()
    return bool(row and row["locked"])


def labels(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT label, may_be_public, public_props, description, locked, status, created_by"
        " FROM kg.label ORDER BY label").fetchall()
    return [{"label": r["label"], "locked": True} if r["locked"] or r["label"].lower() in
            LOCKED_LOWER else r for r in rows]


def edge_types(conn: psycopg.Connection) -> list[dict]:
    return conn.execute("SELECT type, public_props, description, status, created_by"
                        " FROM kg.edge_type ORDER BY type").fetchall()


def catalog(conn: psycopg.Connection, business_id: str) -> list[dict]:
    return conn.execute(
        "SELECT id, name, props, status, visibility FROM kg.node"
        " WHERE business_id = %s AND label = 'UIComponent' ORDER BY id", (business_id,)
    ).fetchall()


def search_nodes(conn: psycopg.Connection, business_id: str, q: str, label: str | None,
                 limit: int = 25) -> list[dict]:
    sql = (
        "SELECT n.id, n.label, n.name, n.props, n.visibility, n.status, n.source_type,"
        " n.verified_by_owner FROM kg.node n JOIN kg.label l ON l.label = n.label"
        f" WHERE n.business_id = %(biz)s AND {READABLE}"
        " AND (%(label)s::text IS NULL OR n.label = %(label)s)"
        " AND (%(q)s = '' OR n.id ILIKE %(like)s OR n.name ILIKE %(like)s"
        "      OR n.search_text ILIKE %(like)s OR n.props::text ILIKE %(like)s)"
        " ORDER BY n.id LIMIT %(limit)s")
    params = {"biz": business_id, "label": label, "q": q, "like": f"%{q}%",
              "limit": limit, "locked": LOCKED_LOWER}
    return conn.execute(sql, params).fetchall()


def edges_among_readable(conn: psycopg.Connection, node_ids: list[str]) -> list[dict]:
    if not node_ids:
        return []
    sql = (
        "SELECT e.id, e.src, e.dst, e.type, e.props, e.status, e.source_type,"
        " e.verified_by_owner FROM kg.edge e"
        " JOIN kg.node n ON n.id = e.src JOIN kg.label l ON l.label = n.label"
        " JOIN kg.node m ON m.id = e.dst JOIN kg.label k ON k.label = m.label"
        " WHERE (e.src = ANY(%(ids)s) OR e.dst = ANY(%(ids)s))"
        " AND l.locked = false AND lower(n.label) <> ALL(%(locked)s)"
        " AND k.locked = false AND lower(m.label) <> ALL(%(locked)s) ORDER BY e.id")
    return conn.execute(sql, {"ids": node_ids, "locked": LOCKED_LOWER}).fetchall()


def agent_changes(conn: psycopg.Connection, business_id: str, state: str | None) -> list[dict]:
    return conn.execute(
        "SELECT id AS change_id, ts, actor, action, target, before, after, reason, evidence,"
        " tier, state, decided_by, decided_at FROM kg.change"
        " WHERE business_id = %s AND actor = 'agent' AND (%s::text IS NULL OR state = %s)"
        " ORDER BY id DESC LIMIT 200", (business_id, state, state)).fetchall()


def start_of_today(tz: str) -> datetime:
    now = datetime.now(ZoneInfo(tz))
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def digest(conn: psycopg.Connection, business_id: str, tz: str) -> dict:
    questions = conn.execute(
        "SELECT count(*) AS n FROM ops.intent_log WHERE business_id = %s AND ts >= %s",
        (business_id, start_of_today(tz))).fetchone()["n"]
    topics = conn.execute(
        "SELECT gap_topic AS topic, count(*) AS count FROM ops.intent_log"
        " WHERE business_id = %s AND gap_topic IS NOT NULL GROUP BY gap_topic"
        " ORDER BY count DESC, topic LIMIT 5", (business_id,)).fetchall()
    gaps = conn.execute(
        "SELECT count(*) AS n FROM kg.node WHERE business_id = %s AND label = 'KnowledgeGap'"
        " AND props ->> 'state' = 'open'", (business_id,)).fetchone()["n"]
    pending = conn.execute("SELECT count(*) AS n FROM kg.change WHERE business_id = %s"
                           " AND state = 'pending'", (business_id,)).fetchone()["n"]
    leads = conn.execute(
        "SELECT kind, count(*) AS count FROM ops.lead WHERE business_id = %s AND status = 'new'"
        " GROUP BY kind ORDER BY kind", (business_id,)).fetchall()
    return {"questions_today": questions, "top_topics": topics, "open_gaps": gaps,
            "pending_changes": pending, "new_leads": leads}
