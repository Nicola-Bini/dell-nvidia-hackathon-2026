"""What only the owner can do: approve, reject, revert and verify (SCHEMA 8.6).

The caller owns the transaction. Every function checks the change's state first, so a double
tap or a stale inbox page answers 409 instead of applying twice.
"""

import psycopg
from cac_common.settings import Settings
from psycopg.types.json import Jsonb

from app.domain.requests import ChangeError, ChangeRequest
from app.services import publisher
from app.services.appliers import HANDLERS, Handler, Written
from app.services.change_engine import reindex


def _load(conn: psycopg.Connection, settings: Settings, change_id: int, wanted: str) -> dict:
    row = conn.execute("SELECT * FROM kg.change WHERE id = %s AND business_id = %s FOR UPDATE",
                       (change_id, settings.business_id)).fetchone()
    if row is None:
        raise ChangeError(404, f"no change {change_id}")
    if row["state"] != wanted:
        raise ChangeError(409, f"change {change_id} is {row['state']}, not {wanted}")
    return row


def _request(change: dict) -> ChangeRequest:
    return ChangeRequest(action=change["action"], target=change["target"],
                         after=change["after"], reason=change["reason"],
                         evidence=change["evidence"])


def _decide(conn: psycopg.Connection, change_id: int, state: str, **extra) -> None:
    conn.execute("UPDATE kg.change SET state = %s, decided_by = 'owner', decided_at = now()"
                 " WHERE id = %s", (state, change_id))
    if "before" in extra:
        conn.execute("UPDATE kg.change SET before = %s WHERE id = %s",
                     (Jsonb(extra["before"]), change_id))
    if "evidence" in extra:
        conn.execute("UPDATE kg.change SET evidence = %s WHERE id = %s",
                     (Jsonb(extra["evidence"]), change_id))


def _apply_now(conn: psycopg.Connection, settings: Settings, change: dict,
               handler: Handler) -> tuple[Written, dict | None]:
    """Make a pending change real: flip a draft to approved, or write the deferred edit."""
    if handler.creates:
        return handler.set_status(conn, change, "approved"), None
    req = _request(change)
    state = handler.state(conn, settings.business_id, req)
    handler.validate(conn, settings.business_id, req, state)
    before = handler.snapshot(conn, settings.business_id, req)
    return handler.write(conn, settings.business_id, req, "approved"), before


def approve(conn: psycopg.Connection, settings: Settings, change_id: int) -> dict:
    change = _load(conn, settings, change_id, "pending")
    written, before = _apply_now(conn, settings, change, HANDLERS[change["action"]])
    reindex(conn, written)
    extra = {} if before is None else {"before": before}
    _decide(conn, change_id, "applied", **extra)
    return {"change_id": change_id, "state": "applied",
            "graph_version": publisher.publish_now(conn, settings)}


def reject(conn: psycopg.Connection, settings: Settings, change_id: int,
           reason: str | None) -> dict:
    change = _load(conn, settings, change_id, "pending")
    handler = HANDLERS[change["action"]]
    if handler.creates:
        handler.set_status(conn, change, "retired")
    evidence = dict(change["evidence"])
    if reason:
        evidence["rejection_reason"] = reason.strip()[:500]
    _decide(conn, change_id, "rejected", evidence=evidence)
    return {"change_id": change_id, "state": "rejected"}


def revert(conn: psycopg.Connection, settings: Settings, change_id: int) -> dict:
    change = _load(conn, settings, change_id, "applied")
    handler = HANDLERS[change["action"]]
    written = (handler.set_status(conn, change, "retired") if handler.creates
               else handler.restore(conn, change))
    reindex(conn, written)
    _decide(conn, change_id, "reverted")
    return {"change_id": change_id, "state": "reverted",
            "graph_version": publisher.publish_now(conn, settings)}


def _mark_verified(conn: psycopg.Connection, table: str, ids: list, kind: str) -> int:
    if not ids:
        return 0
    found = conn.execute(f"SELECT count(*) AS n FROM kg.{table} WHERE id = ANY(%s)",
                         (ids,)).fetchone()["n"]
    if found != len(set(ids)):
        raise ChangeError(404, f"unknown {kind} id in the request")
    conn.execute(f"UPDATE kg.{table} SET verified_by_owner = true, verified_at = now()"
                 " WHERE id = ANY(%s)", (ids,))
    return found


def verify(conn: psycopg.Connection, settings: Settings, node_ids: list[str],
           edge_ids: list[int]) -> dict:
    """Set `verified_by_owner`: the only path to a verified badge."""
    if not node_ids and not edge_ids:
        raise ChangeError(422, "give node_ids or edge_ids")
    nodes = _mark_verified(conn, "node", node_ids, "node")
    edges = _mark_verified(conn, "edge", edge_ids, "edge")
    return {"verified_nodes": nodes, "verified_edges": edges,
            "graph_version": publisher.publish_now(conn, settings)}
