"""Build `kg.node.search_text`: the node name plus its public string props, nothing else.

Private props never reach `search_text`, so the published copy cannot leak them
(docs/SCHEMA.md section 5).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


def _string_leaves(value: Any) -> Iterator[str]:
    """Yield the strings inside `value`; numbers, booleans and nulls are skipped."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _string_leaves(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _string_leaves(item)


def build_search_text(name: str, props: dict, public_props: list[str]) -> str:
    """Return `name` followed by the public props' string values, single-spaced.

    Props are read in `public_props` order, so the result is stable for a given registry row.
    """
    parts = [name]
    for key in public_props:
        parts.extend(_string_leaves(props.get(key)))
    return " ".join(" ".join(parts).split())
