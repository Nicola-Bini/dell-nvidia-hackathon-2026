"""Insert-only request log. cac_serve cannot read ops.intent_log, so no RETURNING here.

The raw visitor text goes to this table and nowhere else: never to application logs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import psycopg
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class LogEntry:
    business_id: str
    channel: str
    session_id: str | None
    text: str
    cache: str
    kind: str
    latency_ms: int
    graph_version: int
    slots: dict = field(default_factory=dict)
    selection: dict | None = None
    gap_topic: str | None = None
    model: str | None = None


def insert(conn: psycopg.Connection, entry: LogEntry) -> None:
    conn.execute(
        "INSERT INTO ops.intent_log (business_id, channel, session_id, text, slots, cache,"
        " selection, kind, gap_topic, latency_ms, model, graph_version)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            entry.business_id, entry.channel, entry.session_id, entry.text,
            Jsonb(entry.slots), entry.cache,
            Jsonb(entry.selection) if entry.selection is not None else None,
            entry.kind, entry.gap_topic, entry.latency_ms, entry.model, entry.graph_version,
        ),
    )
