"""Exact intent cache (SCHEMA 8.5 step 3). Holds the model's selection only: no text."""

from __future__ import annotations

from dataclasses import dataclass

import psycopg
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class CacheKey:
    business_id: str
    graph_version: int
    normalized_hash: str
    slots_key: str

    def as_tuple(self) -> tuple[str, int, str, str]:
        return (self.business_id, self.graph_version, self.normalized_hash, self.slots_key)


_WHERE = (
    " WHERE business_id = %s AND graph_version = %s"
    " AND normalized_hash = %s AND slots_key = %s"
)


def lookup(conn: psycopg.Connection, key: CacheKey) -> dict | None:
    row = conn.execute(
        "SELECT selection FROM ops.intent_cache" + _WHERE, key.as_tuple()
    ).fetchone()
    return row[0] if row else None


def record_hit(conn: psycopg.Connection, key: CacheKey) -> None:
    conn.execute("UPDATE ops.intent_cache SET hits = hits + 1" + _WHERE, key.as_tuple())


def store(conn: psycopg.Connection, key: CacheKey, selection: dict) -> None:
    conn.execute(
        "INSERT INTO ops.intent_cache"
        " (business_id, graph_version, normalized_hash, slots_key, selection)"
        " VALUES (%s, %s, %s, %s, %s)"
        " ON CONFLICT (business_id, graph_version, normalized_hash, slots_key) DO NOTHING",
        (*key.as_tuple(), Jsonb(selection)),
    )
