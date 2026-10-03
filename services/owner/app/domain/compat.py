"""Accept the request shapes the agent's client posts as well as the SCHEMA 8.6 ones.

The agent (agent/cac_owner.py) may send `target` as an object, `evidence` as a string, node
props flat inside `after`, and a form's `fields` as plain names. Everything is rewritten to the
SCHEMA shapes before validation, so stored change records are uniform.
"""

import re
from typing import Any

NODE_RESERVED = ("label", "name", "props", "visibility")
NODE_ACTIONS = ("create_node", "update_node", "retire_node")
EDGE_ACTIONS = ("create_edge", "retire_edge")
COMPONENT_ACTIONS = ("create_component", "update_component")


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower().replace("__", "_")


def _fail(message: str) -> None:
    raise ValueError(message)


def _text_target(action: str, target: dict, after: dict) -> str:
    if action in ("create_label", "add_prop"):
        return str(target.get("label") or _fail("target needs a label"))
    if action == "create_edge_type":
        return str(target.get("type") or target.get("edge_type") or _fail("target needs a type"))
    if action in NODE_ACTIONS:
        if target.get("label"):
            after.setdefault("label", target["label"])
        return str(target.get("node_id") or target.get("id") or _fail("target needs a node_id"))
    if action in EDGE_ACTIONS:
        for key in ("src", "dst", "type"):
            if target.get(key):
                after.setdefault(key, target[key])
        return "|".join((str(after.get("src", "")), str(after.get("type", "")),
                         str(after.get("dst", ""))))
    name = target.get("component") or _fail("target needs a component")
    after.setdefault("component", name)
    if target.get("base"):
        after.setdefault("primitive", target["base"])
    return target.get("id") or "ui_" + _snake(str(name))


def _flat_props(action: str, after: dict) -> None:
    if action in ("create_node", "update_node") and "props" not in after:
        flat = {k: after.pop(k) for k in list(after) if k not in NODE_RESERVED
                and k not in ("verified_by_owner", "verified_at", "source_type", "tier")}
        if flat:
            after["props"] = flat


def _component_shape(after: dict) -> None:
    fields = after.get("fields")
    if isinstance(fields, list):
        after["fields"] = [{"name": f, "type": "text", "label": f.replace("_", " ").title()}
                           if isinstance(f, str) else f for f in fields]
    if "submit" in after:
        after.setdefault("submit_label", after.pop("submit"))


def normalize(raw: Any) -> Any:
    if not isinstance(raw, dict):
        return raw
    out = dict(raw)
    after = dict(out.get("after") or {})
    action = out.get("action")
    if isinstance(out.get("target"), dict):
        out["target"] = _text_target(str(action), out["target"], after)
    if isinstance(out.get("evidence"), str):
        out["evidence"] = {"text": out["evidence"]}
    _flat_props(str(action), after)
    if action in COMPONENT_ACTIONS:
        _component_shape(after)
    out["after"] = after
    return out
