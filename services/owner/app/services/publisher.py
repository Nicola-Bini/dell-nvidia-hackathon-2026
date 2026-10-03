"""The one place that publishes. wp5 adds the pre-warm replay after the commit."""

import psycopg
from cac_common.graph import publish
from cac_common.settings import Settings


def publish_now(conn: psycopg.Connection, settings: Settings) -> int:
    """Copy the approved public graph across the boundary; return the new graph version."""
    return publish(conn, settings.business_id)
