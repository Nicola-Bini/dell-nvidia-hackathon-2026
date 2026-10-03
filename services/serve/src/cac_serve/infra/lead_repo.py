"""Insert-only lead store. cac_serve cannot read ops.lead: no RETURNING, no ON CONFLICT.

The payload holds customer details. It is written here and never logged or echoed.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import psycopg
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class Lead:
    business_id: str
    kind: str
    component: str
    payload: dict
    channel: str
    session_id: str | None


def insert(conn: psycopg.Connection, lead: Lead, lead_id: uuid.UUID | None = None) -> uuid.UUID:
    """Store a lead under a caller-generated id. A duplicate id means "already stored"."""
    lead_id = lead_id or uuid.uuid4()
    try:
        conn.execute(
            "INSERT INTO ops.lead (id, business_id, kind, component, payload, channel,"
            " session_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (lead_id, lead.business_id, lead.kind, lead.component, Jsonb(lead.payload),
             lead.channel, lead.session_id),
        )
    except psycopg.errors.UniqueViolation:
        pass
    return lead_id
