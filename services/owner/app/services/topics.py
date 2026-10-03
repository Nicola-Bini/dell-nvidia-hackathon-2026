"""Clustered visitor topics and knowledge gaps. Raw visitor text never leaves `ops.intent_log`:
only the model's short topic phrase (SCHEMA 8.1, 60 characters) and counts come out."""

import re
from collections import defaultdict

import psycopg
from cac_common.settings import Settings
from psycopg.types.json import Jsonb

from app.domain.requests import ChangeError

WATERMARK = "gap_watermark"
FOLD_LOCK = 7_240_001
MAX_SESSIONS_KEPT = 500
STATES = ("open", "asked", "answered")


def normalize_topic(raw: str) -> str:
    """Lower-case, keep letters, digits and a little punctuation, collapse spaces, cap at 60."""
    text = re.sub(r"[^\w\s'&/-]", " ", str(raw).lower())
    return re.sub(r"\s+", " ", text).strip()[:60].strip()


def slug(text: str, limit: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:limit] or "x"


def _new_rows(conn: psycopg.Connection, biz: str) -> tuple[list[dict], int]:
    mark = conn.execute("SELECT value FROM ops.sync_state WHERE key = %s",
                        (WATERMARK,)).fetchone()
    mark = mark["value"] if mark else 0
    top = conn.execute("SELECT max(id) AS top FROM ops.intent_log WHERE id > %s",
                       (mark,)).fetchone()["top"]
    rows = conn.execute(
        "SELECT id, session_id, gap_topic FROM ops.intent_log WHERE business_id = %s AND id > %s"
        " AND kind = 'gap' AND gap_topic IS NOT NULL ORDER BY id", (biz, mark)).fetchall()
    return rows, top or mark


def _group(rows: list[dict]) -> dict[str, dict]:
    groups: dict[str, dict] = defaultdict(lambda: {"count": 0, "sessions": set()})
    for row in rows:
        topic = normalize_topic(row["gap_topic"])
        if topic:
            groups[topic]["count"] += 1
            groups[topic]["sessions"].add(row["session_id"] or f"anon:{row['id']}")
    return groups


def _gap_node(conn: psycopg.Connection, biz: str, topic: str) -> dict | None:
    return conn.execute(
        "SELECT id, props FROM kg.node WHERE business_id = %s AND label = 'KnowledgeGap'"
        " AND props ->> 'topic' = %s", (biz, topic)).fetchone()


def _free_gap_id(conn: psycopg.Connection, topic: str) -> str:
    base, n = f"gap_{slug(topic)}", 1
    while conn.execute("SELECT 1 FROM kg.node WHERE id = %s", (base if n == 1 else
                                                              f"{base}_{n}",)).fetchone():
        n += 1
    return base if n == 1 else f"{base}_{n}"


def _upsert_gap(conn: psycopg.Connection, biz: str, topic: str, seen: dict) -> None:
    node = _gap_node(conn, biz, topic)
    if node is None:
        sessions = sorted(seen["sessions"])[:MAX_SESSIONS_KEPT]
        props = {"topic": topic, "count": seen["count"], "sessions": len(sessions),
                 "state": "open", "origin": "visitor", "session_ids": sessions}
        conn.execute(
            "INSERT INTO kg.node (id, business_id, label, name, props, visibility, status,"
            " source_type, extracted_by) VALUES (%s, %s, 'KnowledgeGap', %s, %s, 'private',"
            " 'approved', 'agent', 'topics')",
            (_free_gap_id(conn, topic), biz, topic, Jsonb(props)))
        return
    props = dict(node["props"])
    union = sorted(set(props.get("session_ids", [])) | seen["sessions"])[:MAX_SESSIONS_KEPT]
    props.update(count=int(props.get("count", 0)) + seen["count"], sessions=len(union),
                 session_ids=union)
    conn.execute("UPDATE kg.node SET props = %s, updated_at = now() WHERE id = %s",
                 (Jsonb(props), node["id"]))


def fold(conn: psycopg.Connection, settings: Settings) -> int:
    """Fold intent-log rows newer than the watermark into KnowledgeGap nodes."""
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (FOLD_LOCK,))
    rows, top = _new_rows(conn, settings.business_id)
    for topic, seen in _group(rows).items():
        _upsert_gap(conn, settings.business_id, topic, seen)
    conn.execute("INSERT INTO ops.sync_state (key, value) VALUES (%s, %s)"
                 " ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (WATERMARK, top))
    return len(rows)


def _answer_counts(conn: psycopg.Connection, biz: str) -> list[dict]:
    return conn.execute(
        "SELECT v ->> 'component' AS component, count(*) AS count,"
        " count(DISTINCT l.session_id) AS sessions FROM ops.intent_log l,"
        " jsonb_array_elements(CASE WHEN jsonb_typeof(l.selection -> 'views') = 'array'"
        "   THEN l.selection -> 'views' ELSE '[]'::jsonb END) AS v"
        " WHERE l.business_id = %s AND l.kind = 'answer' AND v ->> 'component' IS NOT NULL"
        " GROUP BY 1 ORDER BY count DESC, 1", (biz,)).fetchall()


def _gap_rows(conn: psycopg.Connection, biz: str) -> list[dict]:
    return conn.execute(
        "SELECT id, props FROM kg.node WHERE business_id = %s AND label = 'KnowledgeGap'"
        " ORDER BY (props ->> 'count')::int DESC, id", (biz,)).fetchall()


def topics(conn: psycopg.Connection, settings: Settings) -> list[dict]:
    """`[{ topic, count, sessions, kind, component }]`: gap phrases, then counts per component."""
    fold(conn, settings)
    out = [{"topic": g["props"]["topic"], "count": int(g["props"]["count"]),
            "sessions": int(g["props"]["sessions"]), "kind": "gap", "component": None,
            "state": g["props"]["state"]} for g in _gap_rows(conn, settings.business_id)]
    out += [{"topic": a["component"], "count": a["count"], "sessions": a["sessions"],
             "kind": "answer", "component": a["component"]}
            for a in _answer_counts(conn, settings.business_id)]
    return out


def gaps(conn: psycopg.Connection, settings: Settings, state: str) -> list[dict]:
    """`[{ gap_id, topic, count }]` for gaps seen in at least GAP_ASK_MIN_SESSIONS sessions."""
    if state not in STATES:
        raise ChangeError(422, f"state is one of {', '.join(STATES)}")
    fold(conn, settings)
    return [{"gap_id": g["id"], "topic": g["props"]["topic"], "count": int(g["props"]["count"])}
            for g in _gap_rows(conn, settings.business_id)
            if g["props"]["state"] == state
            and int(g["props"]["sessions"]) >= settings.gap_ask_min_sessions]


def load_gap(conn: psycopg.Connection, settings: Settings, gap_id: str) -> dict:
    row = conn.execute(
        "SELECT id, props FROM kg.node WHERE id = %s AND business_id = %s"
        " AND label = 'KnowledgeGap' FOR UPDATE", (gap_id, settings.business_id)).fetchone()
    if row is None:
        raise ChangeError(404, f"no gap {gap_id!r}")
    return row


def set_gap_state(conn: psycopg.Connection, gap: dict, state: str, **extra) -> None:
    props = {**gap["props"], "state": state, **extra}
    conn.execute("UPDATE kg.node SET props = %s, updated_at = now() WHERE id = %s",
                 (Jsonb(props), gap["id"]))


def mark_asked(conn: psycopg.Connection, settings: Settings, gap_id: str) -> dict:
    """Only one gap is `asked` at a time, so the owner's reply maps to one question."""
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (FOLD_LOCK + 1,))
    gap = load_gap(conn, settings, gap_id)
    if gap["props"]["state"] != "open":
        raise ChangeError(409, f"gap {gap_id} is {gap['props']['state']}, not open")
    other = conn.execute(
        "SELECT id FROM kg.node WHERE business_id = %s AND label = 'KnowledgeGap'"
        " AND props ->> 'state' = 'asked'", (settings.business_id,)).fetchone()
    if other:
        raise ChangeError(409, f"gap {other['id']} is still waiting for the owner's answer")
    set_gap_state(conn, gap, "asked")
    return {"gap_id": gap_id, "state": "asked"}
