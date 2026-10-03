"""Which channel a request came in on. Set by the server from the caller, never the body."""

from __future__ import annotations

import ipaddress

from starlette.requests import Request

CHANNEL_HEADER = "x-cac-channel"
INTERNAL_CHANNELS = frozenset({"mcp", "prewarm"})
_PROXY_HEADERS = ("x-forwarded-for", "forwarded", "x-real-ip")


def _is_loopback(host: str | None) -> bool:
    if not host:
        return False
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def resolve_channel(request: Request) -> str:
    """`mcp` or `prewarm` only for a direct loopback caller that says so; otherwise `web`."""
    claimed = request.headers.get(CHANNEL_HEADER, "").strip().lower()
    if claimed not in INTERNAL_CHANNELS:
        return "web"
    client = request.client
    if client is None or not _is_loopback(client.host):
        return "web"
    if any(header in request.headers for header in _PROXY_HEADERS):
        return "web"  # relayed for someone else by a local proxy or tunnel
    return claimed
