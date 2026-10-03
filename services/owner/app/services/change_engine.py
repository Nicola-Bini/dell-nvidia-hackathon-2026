"""Submit a change: classify, record, and apply it according to its tier (SCHEMA 8.6).

The caller owns the transaction. Nothing is written before the tier is known, and a locked
change is recorded as refused and never touches the graph.
"""

from dataclasses import dataclass

import psycopg
from cac_common.graph import reindex_node
from cac_common.settings import Settings
from psycopg.types.json import Jsonb

from app.domain.requests import ChangeRequest
from app.domain.tiers import Kind, TierDecision, assign_tier
from app.services import publisher
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


@dataclass(frozen=True)
class Plan:
    """What the engine decided about a request before writing anything."""

    target: str
    before: dict | None
    decision: TierDecision
    actor: str = "agent"


def record_change(conn: psycopg.Connection, biz: str, req: ChangeRequest, plan: Plan,
                  state: str) -> int:
    evidence = dict(req.evidence)
    if plan.decision.tier == "locked":
        evidence["refusal"] = plan.decision.reason
    row = conn.execute(
        "INSERT INTO kg.change (business_id, actor, action, target, before, after, reason,"
        " evidence, tier, state, decided_by, decided_at) VALUES (%(biz)s, %(actor)s, %(action)s,"
        " %(target)s, %(before)s, %(after)s, %(reason)s, %(evidence)s, %(tier)s, %(state)s,"
        " CASE WHEN %(actor)s = 'owner' THEN 'owner' END,"
        " CASE WHEN %(actor)s = 'owner' THEN now() END) RETURNING id",
        {"biz": biz, "actor": plan.actor, "action": req.action, "target": plan.target,
         "before": Jsonb(plan.before) if plan.before is not None else None,
         "after": Jsonb(req.after), "reason": req.reason, "evidence": Jsonb(evidence),
         "tier": plan.decision.tier, "state": state}).fetchone()
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
        change_id = record_change(conn, biz, req, Plan(target, None, decision), "rejected")
        return Submitted(change_id, "locked", "rejected", decision.reason)
    handler.validate(conn, biz, req, state)
    before = handler.snapshot(conn, biz, req)
    live = decision.tier == "auto"
    change_id = record_change(conn, biz, req, Plan(target, before, decision),
                              "applied" if live else "pending")
    if live or handler.creates:
        reindex(conn, handler.write(conn, biz, req, "approved" if live else "draft"))
    version = None
    if live and decision.kind != Kind.PRIVATE:
        version = publisher.publish_now(conn, settings)
    return Submitted(change_id, decision.tier, "applied" if live else "pending",
                     graph_version=version)
