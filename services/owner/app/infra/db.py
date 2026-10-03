"""Per-request connection as `cac_owner`. Commits when the route returns, rolls back on error."""

from collections.abc import Iterator

import psycopg
from fastapi import Request
from psycopg.rows import dict_row


def get_conn(request: Request) -> Iterator[psycopg.Connection]:
    url = request.app.state.settings.owner_database_url
    with psycopg.connect(url, row_factory=dict_row) as conn:
        yield conn
