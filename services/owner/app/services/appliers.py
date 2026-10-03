"""One handler per action: look up state, validate, snapshot `before`, write, restore.

Creations (`creates = True`) are written as drafts while they wait for the owner and flipped
to approved on approval. Modifications of something that already exists are not written
until approval, so a pending edit never leaves the published copy.

Lookups run before the tier is known and must not reveal more than the tier rules need;
format checks run in `validate`, after a locked change has already been refused.
"""

from dataclasses import dataclass


from app.domain import requests as rq
from app.domain.requests import ChangeError, ChangeRequest
from app.domain.tiers import NodeState, TargetState, is_locked_label
from app.infra import graph


@dataclass(frozen=True)
class Written:
    """What a write touched: node ids to re-embed."""

    node_ids: tuple[str, ...] = ()


class Handler:
    creates = False

    def canonical_target(self, req: ChangeRequest) -> str:
        return req.target

    def state(self, conn, biz: str, req: ChangeRequest) -> TargetState:
        raise NotImplementedError

    def validate(self, conn, biz: str, req: ChangeRequest, state: TargetState) -> None:
        """Format and conflict checks, run only for changes that are not locked."""

    def snapshot(self, conn, biz: str, req: ChangeRequest) -> dict | None:
        return None

    def write(self, conn, biz: str, req: ChangeRequest, status: str) -> Written:
        raise NotImplementedError

    def set_status(self, conn, change: dict, status: str) -> Written:
        """Creations only: move the created thing to `status` (approved or retired)."""
        raise NotImplementedError

    def restore(self, conn, change: dict) -> Written:
        """Modifications only: put `before` back."""
        raise NotImplementedError


def _label_state(conn, name: str) -> TargetState:
    row = graph.get_label(conn, name)
    if row is None:
        return TargetState(label=name)
    return TargetState(label=name, label_exists=True, label_public=row["may_be_public"],
                       label_locked=bool(row["locked"]))


def _require_label(conn, name: str) -> dict:
    row = graph.get_label(conn, name)
    if row is None:
        raise ChangeError(422, f"unknown label {name!r}; create it first")
    return row


def _require_node(conn, node_id: str) -> dict:
    node = graph.get_node(conn, node_id)
    if node is None:
        raise ChangeError(404, f"no node {node_id!r}")
    return node


class CreateLabel(Handler):
    creates = True

    def state(self, conn, biz, req):
        return _label_state(conn, req.target)

    def validate(self, conn, biz, req, state):
        if state.label_exists:
            raise ChangeError(409, f"label {req.target!r} already exists")
        if not rq.LABEL_RE.match(req.target):
            raise ChangeError(422, f"label name must match {rq.LABEL_RE.pattern}")
        if req.after.get("public_props"):
            rq.prop_names({"public_props": req.after["public_props"]})

    def write(self, conn, biz, req, status):
        graph.insert_label(conn, req.target, req.after, status)
        return Written()

    def set_status(self, conn, change, status):
        graph.set_label_status(conn, change["target"], status)
        return Written()


class AddProp(Handler):
    def state(self, conn, biz, req):
        _require_label(conn, req.target)
        return _label_state(conn, req.target)

    def validate(self, conn, biz, req, state):
        rq.prop_names(req.after)

    def snapshot(self, conn, biz, req):
        return {"public_props": list(_require_label(conn, req.target)["public_props"])}

    def write(self, conn, biz, req, status):
        current = list(_require_label(conn, req.target)["public_props"])
        merged = current + [n for n in rq.prop_names(req.after) if n not in current]
        graph.set_public_props(conn, req.target, merged)
        return Written()

    def restore(self, conn, change):
        graph.set_public_props(conn, change["target"], change["before"]["public_props"])
        return Written()


class CreateEdgeType(Handler):
    creates = True

    def state(self, conn, biz, req):
        return TargetState(label_exists=graph.get_edge_type(conn, req.target) is not None)

    def validate(self, conn, biz, req, state):
        if state.label_exists:
            raise ChangeError(409, f"edge type {req.target!r} already exists")
        if not rq.EDGE_TYPE_RE.match(req.target):
            raise ChangeError(422, f"edge type must match {rq.EDGE_TYPE_RE.pattern}")

    def write(self, conn, biz, req, status):
        graph.insert_edge_type(conn, req.target, req.after, status)
        return Written()

    def set_status(self, conn, change, status):
        graph.set_edge_type_status(conn, change["target"], status)
        return Written()


class CreateNode(Handler):
    creates = True

    def state(self, conn, biz, req):
        name = str(req.after.get("label", ""))
        state = _label_state(conn, name)
        if not state.label_exists and not is_locked_label(name):
            raise ChangeError(422, f"unknown label {name!r}; create it first")
        return state

    def validate(self, conn, biz, req, state):
        rq.check_id(req.target, "node id")
        if graph.get_node(conn, req.target):
            raise ChangeError(409, f"node {req.target!r} already exists")
        name = str(req.after.get("name", "")).strip()
        if not name or len(name) > 200:
            raise ChangeError(422, "a node needs a name of at most 200 characters")
        rq.check_props(req.after.get("props"))

    def _node(self, conn, req) -> dict:
        label = _require_label(conn, str(req.after["label"]))
        wanted = req.after.get("visibility", "public")
        visible = "public" if label["may_be_public"] and wanted == "public" else "private"
        return {"label": label["label"], "name": str(req.after["name"]).strip(),
                "props": rq.check_props(req.after.get("props")), "visibility": visible}

    def write(self, conn, biz, req, status):
        graph.insert_node(conn, biz, req.target, self._node(conn, req), status)
        return Written((req.target,))

    def set_status(self, conn, change, status):
        graph.set_node_status(conn, change["target"], status)
        return Written((change["target"],))


class UpdateNode(Handler):
    def state(self, conn, biz, req):
        node = _require_node(conn, req.target)
        return TargetState(label=node["label"], node=graph.node_state(conn, node))

    def validate(self, conn, biz, req, state):
        node = _require_node(conn, req.target)
        if node["status"] == "retired":
            raise ChangeError(409, f"node {req.target!r} is retired")
        rq.check_props(req.after.get("props"))
        if "name" in req.after and not str(req.after["name"]).strip():
            raise ChangeError(422, "name cannot be empty")
        if req.after.get("visibility", node["visibility"]) not in ("public", "private"):
            raise ChangeError(422, "visibility is public or private")

    def snapshot(self, conn, biz, req):
        node = _require_node(conn, req.target)
        return {k: node[k] for k in ("name", "props", "visibility", "status")}

    def write(self, conn, biz, req, status):
        node = _require_node(conn, req.target)
        props = {**node["props"], **rq.check_props(req.after.get("props"))}
        graph.update_node(conn, node["id"], str(req.after.get("name", node["name"])).strip(),
                          props, req.after.get("visibility", node["visibility"]), node["status"])
        return Written((node["id"],))

    def restore(self, conn, change):
        b = change["before"]
        graph.update_node(conn, change["target"], b["name"], b["props"], b["visibility"],
                          b["status"])
        return Written((change["target"],))


class RetireNode(UpdateNode):
    def validate(self, conn, biz, req, state):
        _require_node(conn, req.target)

    def write(self, conn, biz, req, status):
        graph.set_node_status(conn, req.target, "retired")
        return Written((req.target,))


def _edge_key(req: ChangeRequest) -> tuple[str, str, str]:
    a = req.after
    if a.get("src") and a.get("dst") and a.get("type"):
        return str(a["src"]), str(a["dst"]), str(a["type"])
    parts = req.target.split("|")
    if len(parts) != 3 or not all(parts):
        raise ChangeError(422, "an edge is named by after.{src,dst,type} or 'src|TYPE|dst'")
    return parts[0], parts[2], parts[1]


def edge_target(key: tuple[str, str, str]) -> str:
    return f"{key[0]}|{key[2]}|{key[1]}"


class CreateEdge(Handler):
    creates = True

    def canonical_target(self, req):
        return edge_target(_edge_key(req))

    def state(self, conn, biz, req):
        src, dst, edge_type = _edge_key(req)
        ends = []
        for node_id in (src, dst):
            node = graph.get_node(conn, node_id)
            if node is None:
                raise ChangeError(422, f"no node {node_id!r}")
            ends.append(graph.node_state(conn, node))
        if graph.get_edge_type(conn, edge_type) is None:
            raise ChangeError(422, f"unknown edge type {edge_type!r}; create it first")
        return TargetState(src=ends[0], dst=ends[1], edge_type=edge_type)

    def validate(self, conn, biz, req, state):
        existing = graph.get_edge(conn, *_edge_key(req))
        if existing and existing["status"] != "retired":
            raise ChangeError(409, "that edge already exists")
        rq.check_props(req.after.get("props"))

    def write(self, conn, biz, req, status):
        key = _edge_key(req)
        graph.upsert_edge(conn, biz, key, rq.check_props(req.after.get("props")), status)
        return Written()

    def set_status(self, conn, change, status):
        src, typ, dst = change["target"].split("|")
        graph.set_edge_status(conn, (src, dst, typ), status)
        return Written()


class RetireEdge(Handler):
    def canonical_target(self, req):
        return edge_target(_edge_key(req))

    def state(self, conn, biz, req):
        key = _edge_key(req)
        edge = graph.get_edge(conn, *key)
        if edge is None:
            raise ChangeError(404, "no such edge")
        ends = [graph.node_state(conn, graph.get_node(conn, n)) for n in key[:2]]
        return TargetState(src=ends[0], dst=ends[1], edge_type=key[2],
                           edge_verified=edge["verified_by_owner"])

    def snapshot(self, conn, biz, req):
        return {"status": graph.get_edge(conn, *_edge_key(req))["status"]}

    def write(self, conn, biz, req, status):
        graph.set_edge_status(conn, _edge_key(req), "retired")
        return Written()

    def restore(self, conn, change):
        src, typ, dst = change["target"].split("|")
        graph.set_edge_status(conn, (src, dst, typ), change["before"]["status"])
        return Written()


class CreateComponent(CreateNode):
    def state(self, conn, biz, req):
        return _label_state(conn, "UIComponent")

    def validate(self, conn, biz, req, state):
        if not state.label_exists:
            raise ChangeError(422, "the UIComponent label is missing from the registry")
        rq.check_id(req.target, "component id")
        if graph.get_node(conn, req.target):
            raise ChangeError(409, f"component {req.target!r} already exists")
        rq.catalog_entry(req.after)

    def write(self, conn, biz, req, status):
        entry = rq.catalog_entry(req.after)
        node = {"label": "UIComponent", "name": entry["component"], "props": entry,
                "visibility": "public"}
        graph.insert_node(conn, biz, req.target, node, status)
        return Written((req.target,))


class UpdateComponent(UpdateNode):
    def state(self, conn, biz, req):
        node = _require_node(conn, req.target)
        if node["label"] != "UIComponent":
            raise ChangeError(422, f"{req.target!r} is not an element")
        return super().state(conn, biz, req)

    def validate(self, conn, biz, req, state):
        node = _require_node(conn, req.target)
        rq.catalog_entry(req.after, node["props"])

    def write(self, conn, biz, req, status):
        node = _require_node(conn, req.target)
        entry = rq.catalog_entry(req.after, node["props"])
        graph.update_node(conn, node["id"], entry["component"], entry, node["visibility"],
                          node["status"])
        return Written((node["id"],))


HANDLERS: dict[str, Handler] = {
    "create_label": CreateLabel(), "add_prop": AddProp(), "create_edge_type": CreateEdgeType(),
    "create_node": CreateNode(), "update_node": UpdateNode(), "retire_node": RetireNode(),
    "create_edge": CreateEdge(), "retire_edge": RetireEdge(),
    "create_component": CreateComponent(), "update_component": UpdateComponent(),
}
