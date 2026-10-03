"""What the owner's inbox shows. Leads carry their details here, and only here: the inbox
credential is the owner's, and the page is never tunnelled."""

import psycopg

CHANGE_COLS = ("id AS change_id, ts, actor, action, target, before, after, reason, evidence,"
               " tier, state, decided_by, decided_at")


def pending(conn: psycopg.Connection, biz: str) -> list[dict]:
    return conn.execute(f"SELECT {CHANGE_COLS} FROM kg.change WHERE business_id = %s"
                        " AND state = 'pending' ORDER BY id", (biz,)).fetchall()


def applied(conn: psycopg.Connection, biz: str, limit: int = 30) -> list[dict]:
    return conn.execute(f"SELECT {CHANGE_COLS} FROM kg.change WHERE business_id = %s"
                        " AND state = 'applied' ORDER BY id DESC LIMIT %s",
                        (biz, limit)).fetchall()


def unverified_tags(conn: psycopg.Connection, biz: str, limit: int = 50) -> list[dict]:
    return conn.execute(
        "SELECT e.id AS edge_id, e.src, s.name AS src_name, e.dst, d.name AS dst_name, e.type,"
        " e.status, e.source_type FROM kg.edge e JOIN kg.node s ON s.id = e.src"
        " JOIN kg.node d ON d.id = e.dst WHERE e.business_id = %s AND NOT e.verified_by_owner"
        " AND e.status IN ('approved', 'draft')"
        " AND e.type IN ('SUITABLE_FOR', 'CONTAINS_ALLERGEN')"
        " ORDER BY (e.source_type = 'agent') DESC, e.id DESC LIMIT %s", (biz, limit)).fetchall()


def new_leads(conn: psycopg.Connection, biz: str, limit: int = 50) -> list[dict]:
    return conn.execute(
        "SELECT id::text AS lead_id, ts, kind, component, payload, channel FROM ops.lead"
        " WHERE business_id = %s AND status = 'new' ORDER BY ts DESC LIMIT %s",
        (biz, limit)).fetchall()


def open_gaps(conn: psycopg.Connection, biz: str) -> list[dict]:
    rows = conn.execute(
        "SELECT id AS gap_id, props FROM kg.node WHERE business_id = %s"
        " AND label = 'KnowledgeGap' AND props ->> 'state' IN ('open', 'asked')"
        " ORDER BY id", (biz,)).fetchall()
    return [{"gap_id": r["gap_id"], "topic": r["props"].get("topic"),
             "count": int(r["props"].get("count") or 0), "state": r["props"].get("state")}
            for r in rows]


def build(conn: psycopg.Connection, biz: str) -> dict:
    return {"pending": pending(conn, biz), "unverified_tags": unverified_tags(conn, biz),
            "applied": applied(conn, biz), "leads": new_leads(conn, biz),
            "gaps": open_gaps(conn, biz)}
