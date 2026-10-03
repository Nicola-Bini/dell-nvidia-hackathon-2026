"""Start-up guard: model and embedder endpoints must be on this machine (SCHEMA section 2)."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlsplit


def _is_loopback(address: str) -> bool:
    try:
        return ipaddress.ip_address(address.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def resolve_host(host: str) -> list[str]:
    """Every address the host name resolves to (raises OSError when it does not resolve)."""
    infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return sorted({info[4][0] for info in infos})


def is_own_address(address: str) -> bool:
    """True when the address is assigned to one of this machine's interfaces.

    Binding succeeds only for addresses the machine owns; nothing is sent on the network.
    """
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_DGRAM) as probe:
            probe.bind((address, 0))
    except OSError:
        return False
    return True


def assert_local(
    url: str,
    var_name: str,
    *,
    resolve: Callable[[str], list[str]] = resolve_host,
    is_own: Callable[[str], bool] = is_own_address,
) -> None:
    """Raise RuntimeError naming `var_name` unless the URL's host is loopback or this machine."""
    try:
        host = urlsplit(url).hostname
    except ValueError:
        host = None
    if not host:
        raise RuntimeError(f"{var_name} has no host; it must point at a local endpoint")
    if host == "localhost" or _is_loopback(host):
        return
    try:
        addresses = resolve(host)
    except OSError as exc:
        raise RuntimeError(f"{var_name} host {host!r} does not resolve: {exc}") from exc
    foreign = [a for a in addresses if not _is_loopback(a) and not is_own(a)]
    if foreign or not addresses:
        raise RuntimeError(
            f"{var_name} host {host!r} is not this machine; refusing to start. Models must be"
            " local: use a loopback address or one of this machine's own addresses"
        )
