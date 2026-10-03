"""Submit a change: classify, record, and apply it according to its tier (SCHEMA 8.6).

The caller owns the transaction. Nothing is written before the tier is known, and a locked
change is recorded as refused and never touches the graph.
"""

from dataclasses import dataclass

import psycopg
from cac_common.graph import publish, reindex_node
from cac_common.settings import Settings
from psycopg.types.json import Jsonb

from app.domain.requests import ChangeRequest
from app.domain.tiers import Kind, TierDecision, assign_tier
from app.services.appliers import HANDLERS, Written


@dataclass(frozen=True)
class Submitted:
    change_id: int
    tier: str
    state: str
    reason: str | None = None
    graph_version: int | None = None

    def body(self) -> dict:
        out = {"change_id": self.change_id, "tier": self.tier, "state": self.state}
        if self.reason:
            out["reason"] = self.reason
        if self.graph_version is not None:
            out["graph_version"] = self.graph_version
        return out


def record_change(conn: psycopg.Connection, biz: str, req: ChangeRequest, target: str,
                  before: dict | None, decision: TierDecision, state: str) -> int:
    evidence = dict(req.evidence)
    if decision.tier == "locked":
        evidence["refusal"] = decision.reason
    row = conn.execute(
        "INSERT INTO kg.change (business_id, actor, action, target, before, after, reason,"
        " evidence, tier, state) VALUES (%s, 'agent', %s, %s, %s, %s, %s, %s, %s, %s)"
        " RETURNING id",
        (biz, req.action, target, Jsonb(before) if before is not None else None,
         Jsonb(req.after), req.reason, Jsonb(evidence), decision.tier, state)).fetchone()
    return row["id"]


def reindex(conn: psycopg.Connection, written: Written) -> None:
    for node_id in written.node_ids:
        reindex_node(conn, node_id)


def submit(conn: psycopg.Connection, settings: Settings, req: ChangeRequest) -> Submitted:
    biz = settings.business_id
    handler = HANDLERS[req.action]
    target = handler.canonical_target(req)
    state = handler.state(conn, biz, req)
    decision = assign_tier(req.action, state, req.after, settings.autonomy)
    if decision.tier == "locked":
        change_id = record_change(conn, biz, req, target, None, decision, "rejected")
        return Submitted(change_id, "locked", "rejected", decision.reason)
    handler.validate(conn, biz, req, state)
    before = handler.snapshot(conn, biz, req)
    live = decision.tier == "auto"
    change_id = record_change(conn, biz, req, target, before, decision,
                              "applied" if live else "pending")
    if live or handler.creates:
        reindex(conn, handler.write(conn, biz, req, "approved" if live else "draft"))
    version = None
    if live and decision.kind != Kind.PRIVATE:
        version = publish(conn, biz)
    return Submitted(change_id, decision.tier, "applied" if live else "pending",
                     graph_version=version)
