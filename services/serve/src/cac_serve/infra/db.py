"""The Serve API's one connection pool. It connects only as `cac_serve`.

`snapshot()` gives every read in a request the same view of kg_public (SCHEMA 8.3 rule 10);
`writer()` is for the insert-only log and lead tables.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool

_lock = threading.Lock()
_pool: ConnectionPool | None = None
_users = 0


def open_pool(conninfo: str, min_size: int = 1, max_size: int = 8) -> None:
    """Open the shared pool (called from the app lifespan). Does not wait for the database."""
    global _pool, _users
    with _lock:
        if _pool is None:
            _pool = ConnectionPool(
                conninfo, min_size=min_size, max_size=max_size, open=False,
                kwargs={"autocommit": True}, check=ConnectionPool.check_connection,
                name="cac_serve",
            )
            _pool.open(wait=False)
        _users += 1


def close_pool() -> None:
    global _pool, _users
    with _lock:
        _users = max(0, _users - 1)
        if _users == 0 and _pool is not None:
            _pool.close()
            _pool = None


def _require_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("database pool is not open; the app lifespan opens it")
    return _pool


@contextmanager
def snapshot(timeout: float | None = None) -> Iterator[psycopg.Connection]:
    """A connection inside one REPEATABLE READ, READ ONLY transaction."""
    with _require_pool().connection(timeout) as conn, conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        yield conn


@contextmanager
def writer(timeout: float | None = None) -> Iterator[psycopg.Connection]:
    """An autocommit connection for inserts (no RETURNING: cac_serve cannot read them back)."""
    with _require_pool().connection(timeout) as conn:
        yield conn
