"""Move 3 of the CAC agent: grow the graph (stdlib only, so it runs inside the sandbox).

Code picks one task per heartbeat from the live schema, graph and topics; the model makes the
judgment and hands back a list of changes; code orders, de-duplicates and posts them. Nothing
here names a business, a type or a topic: it works on whatever graph it finds.
SCHEMA section 8.6 is the contract.
"""
import json
import os
import string
from pathlib import Path
from urllib.parse import quote

STATE = Path(__file__).resolve().parent / "grow_state.json"
PAGE = 25            # /owner/graph/search returns at most this many nodes, with no offset
MAX_SEARCHES = 400   # per label, so a huge graph cannot stall a heartbeat
SWEEP = string.ascii_lowercase + string.digits
BATCH = 8            # nodes per classify turn
TAG_MAX = 20         # a type this small can serve as a set of tags
MAX_CHANGES = 25     # per turn
MAX_PENDING = 6      # owner backlog above which only classify runs
MIN_TOPIC_COUNT = 2
ROTATION = ("classify", "topics", "classify", "invent")
ORDER = ("create_label", "add_prop", "create_edge_type", "create_node", "update_node",
         "create_component", "update_component", "create_edge", "retire_edge", "retire_node")
STRUCTURE = ("create_label", "add_prop", "create_edge_type", "create_component")
UI_LABEL = "UIComponent"
ROOT_LABEL = "Business"
UNKNOWN = "Pending owner confirmation"

NAMING = ("type names LikeThis; edge types LIKE_THIS; props and ids like_this; a node id is "
          "a short prefix for its type, an underscore, then a short name")
SHAPES = {
    "create_edge": {"action": "create_edge", "target": "src_id|EDGE_TYPE|dst_id",
                    "reason": "what on the node says so"},
    "create_label": {"action": "create_label", "target": "TypeName", "reason": "...",
                     "after": {"public_props": ["prop_a"], "may_be_public": True,
                               "description": "what this type is"}},
    "create_edge_type": {"action": "create_edge_type", "target": "EDGE_TYPE", "reason": "...",
                         "after": {"description": "FromType -> ToType: what it means"}},
    "create_node": {"action": "create_node", "target": "prefix_short_name", "reason": "...",
                    "after": {"label": "TypeName", "name": "Shown name",
                              "props": {"prop_a": "value"}}},
    "add_prop": {"action": "add_prop", "target": "TypeName", "reason": "...",
                 "after": {"props": ["new_prop"]}},
    "update_node": {"action": "update_node", "target": "node_id", "reason": "...",
                    "after": {"props": {"prop_a": "value"}}},
    "create_component": {
        "action": "create_component", "target": "ui_short_name", "reason": "...",
        "after": {"component": "CamelName", "primitive": "ListCard or FactCard or FormCard",
                  "use_when": "the visitor ...", "rail_label": "Short title",
                  "binds": {"labels": ["TypeName"]},
                  "fields": [{"name": "field_a", "label": "Field A", "required": True,
                              "type": "text or number or date or select"}]}},
}
FACTS = ("Never invent a fact (a price, a time, an ingredient, a policy, a contact detail). "
         f"For a value you do not know write '{UNKNOWN}'. Everything you add is unverified "
         "until the owner confirms it.")
HOW = {
    "classify": (
        "Read each node in 'nodes'. Using only what its own name and props say, add what is "
        "missing. (1) A create_edge from the node to every tag in 'tags' that clearly applies, "
        "with an edge type from 'edge_types' whose description and 'seen' pattern fit. (2) A "
        "create_edge between two nodes that clearly belong together, where an edge type fits. "
        "(3) If these nodes could usefully be sorted in a way that has no tags or edge type "
        "yet, create them first (create_label, one create_node per tag, create_edge_type), "
        "then use them. Skip what a node's 'links' already has. If you are not sure, leave "
        "it out. Return [] if nothing is missing. " + FACTS),
    "topics": (
        "Visitors keep asking about 'topic' and the site had no answer. Decide which it is. "
        "(a) One missing fact only the owner knows: return []; the owner will be asked. "
        "(b) A kind of thing, or a request, that the site has no place for: build the place. "
        "Reuse a type in 'types' or an element in 'elements' when one fits. Otherwise create "
        "the type (create_label), draft nodes when that kind of thing has a few obvious "
        "entries, and an element so visitors can see it or ask for it (create_component: "
        "ListCard lists the nodes of a type, FactCard shows one node, FormCard takes a "
        "request and needs 'fields'). " + FACTS),
    "invent": (
        "Think about what a visitor expects from the site of a business like the one in "
        "'about', and compare that with 'types' and 'elements'. Propose at most 3 things "
        "that are missing and clearly useful, the most useful first: an element that lists "
        "or shows a type in 'unshown' (frequent questions, for example); a form for a request "
        "visitors commonly make; a prop or a set of tags visitors would filter by; an edge "
        "type between two types that belong together. Do not repeat anything in 'already', "
        "whatever its state: rejected means the owner said no. Return [] if nothing is "
        "clearly missing. " + FACTS),
}


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    try:
        STATE.write_text(json.dumps(state))
    except OSError:
        pass  # read-only sandbox: the rotation restarts each turn, nothing else breaks


def search(api, label: str, q: str = "") -> dict:
    res = api.call("GET", f"/owner/graph/search?label={quote(label)}&q={quote(q)}")
    return res if isinstance(res, dict) and "nodes" in res else {"nodes": [], "edges": []}


def nodes_of(api, label: str) -> tuple[dict, dict]:
    """Every node of a label and the edges touching them, keyed by id. A full page is split
    by id prefix (ids are `<prefix>_<name>`) until the pages come back short."""
    nodes, edges, calls = {}, {}, 0

    def pull(q: str) -> bool:
        res = search(api, label, q)
        nodes.update((n["id"], n) for n in res["nodes"])
        edges.update((e["id"], e) for e in res["edges"])
        return len(res["nodes"]) >= PAGE

    if pull(""):
        common = os.path.commonprefix(list(nodes))
        prefix = common[:common.index("_") + 1] if "_" in common else ""
        queue = [prefix + c for c in SWEEP]
        while queue and calls < MAX_SEARCHES:
            q, calls = queue.pop(), calls + 1
            if pull(q):
                queue += [q + c for c in SWEEP + "_"]
    return nodes, edges


def trim(props: dict) -> dict:
    out = {}
    for key, value in (props or {}).items():
        if value not in (None, "", [], {}):
            out[key] = value[:160] if isinstance(value, str) else value
    return out


class World:
    """What the agent may read, fetched once per heartbeat and only when a task needs it."""

    def __init__(self, api):
        self.api = api
        schema = api.call("GET", "/owner/schema")
        self.schema = schema if isinstance(schema, dict) else {}
        self.labels = [row for row in self.schema.get("labels", [])
                       if not row.get("locked") and row["label"] != UI_LABEL
                       and row.get("status") != "retired"]
        changes = api.call("GET", "/owner/changes")
        self.changes = changes if isinstance(changes, list) else []
        self._graph: dict[str, tuple[dict, dict]] = {}

    def graph(self, label: str) -> tuple[dict, dict]:
        if label not in self._graph:
            nodes, edges = nodes_of(self.api, label)
            live = {i: n for i, n in nodes.items() if n.get("status") != "retired"}
            self._graph[label] = (live, edges)
        return self._graph[label]

    def sized(self) -> list[str]:
        """Types that have nodes, the largest first."""
        counts = [(len(self.graph(row["label"])[0]), row["label"]) for row in self.labels]
        return [label for n, label in sorted(counts, key=lambda c: (-c[0], c[1])) if n]

    def pending(self) -> int:
        return sum(1 for c in self.changes if c.get("state") == "pending")

    def elements(self) -> list[dict]:
        out = []
        for row in self.schema.get("catalog", []):
            props = row.get("props") or {}
            if row.get("status") != "retired":
                out.append({"component": props.get("component") or row.get("name"),
                            "use_when": props.get("use_when"),
                            "primitive": props.get("primitive"),
                            "labels": (props.get("binds") or {}).get("labels") or []})
        return out

    def types(self) -> list[dict]:
        return [{"type": row["label"], "props": row.get("public_props") or [],
                 "nodes": len(self.graph(row["label"])[0])} for row in self.labels]


def covered_topics(changes: list) -> set[str]:
    """Topics an agent change (pending or applied) was already made for."""
    return {str(c["evidence"]["topic"]).lower() for c in changes
            if c.get("state") in ("pending", "applied")
            and isinstance(c.get("evidence"), dict) and c["evidence"].get("topic")}


def node_view(node: dict, edges: dict) -> dict:
    links = [f"{e['type']} -> {e['dst']}" for e in edges.values()
             if e["src"] == node["id"] and e.get("status") != "retired"]
    links += [f"{e['type']} <- {e['src']}" for e in edges.values()
              if e["dst"] == node["id"] and e.get("status") != "retired"]
    return {"id": node["id"], "name": node["name"], "props": trim(node.get("props")),
            "links": sorted(links)}


def edge_type_views(world: World, sized: list[str]) -> list[dict]:
    label_of, edges = {}, {}
    for label in sized:
        nodes, found = world.graph(label)
        label_of.update((i, label) for i in nodes)
        edges.update(found)
    seen: dict[str, set] = {}
    for e in edges.values():
        if e["src"] in label_of and e["dst"] in label_of:
            seen.setdefault(e["type"], set()).add(f"{label_of[e['src']]} -> {label_of[e['dst']]}")
    return [{"type": t["type"], "description": t.get("description"),
             "seen": sorted(seen.get(t["type"], ()))}
            for t in world.schema.get("edge_types", []) if t.get("status") != "retired"]


def classify_task(world: World, state: dict) -> dict | None:
    """The next batch of nodes, one type at a time, largest type first, then round again."""
    sized = world.sized()
    if not sized:
        return None
    cursor = state.setdefault("cursor", {})
    label = next((name for name in sized if cursor.get(name, 0) < len(world.graph(name)[0])),
                 None)
    if label is None:
        cursor.clear()
        label = sized[0]
    nodes, edges = world.graph(label)
    start = cursor.get(label, 0)
    batch = sorted(nodes)[start:start + BATCH]
    cursor[label] = start + len(batch)
    tags = {name: [{"id": n["id"], "name": n["name"]} for n in world.graph(name)[0].values()]
            for name in sized if name != label and len(world.graph(name)[0]) <= TAG_MAX}
    return {"task": "classify", "label": label,
            "why": f"review of {len(batch)} {label} nodes against the rest of the graph",
            "nodes": [node_view(nodes[i], edges) for i in batch], "tags": tags,
            "edge_types": edge_type_views(world, sized),
            "shapes": [SHAPES[k] for k in ("create_edge", "create_label", "create_node",
                                           "create_edge_type")]}


def topics_task(world: World, state: dict) -> dict | None:
    """The most-asked unanswered topic that nothing was built for and no turn has weighed."""
    if world.pending() > MAX_PENDING:
        return None
    topics = world.api.call("GET", "/owner/topics")
    seen = state.setdefault("topics_seen", [])
    skip = covered_topics(world.changes) | set(seen)
    open_ = [t for t in topics if t.get("kind") == "gap" and t.get("state") != "answered"
             and t["count"] >= MIN_TOPIC_COUNT and t["topic"].lower() not in skip] \
        if isinstance(topics, list) else []
    if not open_:
        return None
    top = max(open_, key=lambda t: t["count"])
    seen.append(top["topic"].lower())
    why = f"{top['count']} visitors in {top['sessions']} sessions asked about {top['topic']}"
    return {"task": "topics", "topic": top["topic"], "why": why, "types": world.types(),
            "elements": world.elements(), "shapes": list(SHAPES.values())}


def invent_task(world: World, state: dict) -> dict | None:
    """What a site like this should have and does not: types, tags, props, elements."""
    if world.pending() > MAX_PENDING:
        return None
    elements = world.elements()
    shown = {label for e in elements for label in e["labels"]}
    about = [{"name": n["name"], "props": trim(n.get("props"))}
             for n in world.graph(ROOT_LABEL)[0].values()]
    already = [f"{c['action']} {c['target']} ({c.get('state')})" for c in world.changes
               if c.get("action") in STRUCTURE]
    return {"task": "invent", "why": "review of what the site can show against what it holds",
            "about": about, "types": world.types(), "elements": elements,
            "unshown": [name for name in world.sized() if name not in shown],
            "already": already, "shapes": [SHAPES[k] for k in STRUCTURE]}


BUILDERS = {"classify": classify_task, "topics": topics_task, "invent": invent_task}


def next_task(api) -> dict:
    """One work packet for this heartbeat. `apply_changes` reads back what it was."""
    state, world = load_state(), World(api)
    turn = state.get("turn", 0)
    packet = None
    for step in range(len(ROTATION)):
        name = ROTATION[(turn + step) % len(ROTATION)]
        packet = BUILDERS[name](world, state)
        if packet:
            break
    state["turn"] = turn + 1
    if not packet:
        state["task"] = None
        save_state(state)
        return {"task": None}
    state["task"] = {k: packet[k] for k in ("task", "why", "topic") if k in packet}
    save_state(state)
    return {**packet, "how": HOW[packet["task"]], "naming": NAMING,
            "answer": "one JSON list of changes shaped like 'shapes'; [] when there is nothing"}


def target_key(action: str, target, after: dict) -> str:
    """The target as the API stores it, so a change can be matched against past ones."""
    if not isinstance(target, dict):
        return str(target)
    if action in ("create_edge", "retire_edge"):
        ends = {**after, **target}
        return f"{ends.get('src', '')}|{ends.get('type', '')}|{ends.get('dst', '')}"
    for key in ("node_id", "id", "label", "type", "edge_type", "component"):
        if target.get(key):
            return str(target[key])
    return json.dumps(target, sort_keys=True)


def parse_changes(text: str) -> list | None:
    """The JSON list inside a model's answer, which may wrap it in prose or a code fence."""
    start, end = text.find("["), text.rfind("]")
    try:
        found = json.loads(text[start:end + 1]) if 0 <= start < end else None
    except ValueError:
        return None
    return found if isinstance(found, list) else None


def summary(task: str, out: dict) -> str:
    if not out["applied"] and not out["pending"]:
        return f"{task}: nothing new"
    refused = f", {len(out['refused'])} refused" if out["refused"] else ""
    return (f"{task}: {out['applied']} live, {out['pending']} waiting for your approval in "
            f"the inbox{refused}")


def post_change(api, ch: dict, evidence: dict, done: set) -> tuple[str, dict | None]:
    """Post one change. Returns its outcome (applied, pending, skipped or refused)."""
    after = ch.get("after") if isinstance(ch.get("after"), dict) else {}
    key = (ch["action"], target_key(ch["action"], ch.get("target"), after))
    if key in done:
        return "skipped", None
    done.add(key)
    target = key[1] if ch["action"] in ("create_edge", "retire_edge") else ch.get("target")
    res = api.call("POST", "/owner/changes", {
        "action": ch["action"], "target": target, "after": after,
        "reason": str(ch.get("reason") or evidence["text"])[:500], "evidence": evidence})
    res = res if isinstance(res, dict) else {}
    if res.get("state") in ("applied", "pending"):
        return res["state"], None
    if res.get("error") == 409:  # it already exists
        return "skipped", None
    why = res.get("detail") or res.get("reason") or res
    return "refused", {"change": " ".join(key), "why": str(why)[:160]}


def apply_changes(api, changes: list) -> dict:
    """Post the model's changes for the task `next_task` handed out: structure before the
    nodes and edges that use it, nothing the agent already proposed, evidence from the task."""
    task = load_state().get("task") or {}
    evidence = {"text": task.get("why", "review of the graph"), "task": task.get("task", "grow")}
    if task.get("topic"):
        evidence["topic"] = task["topic"]
    past = api.call("GET", "/owner/changes")
    done = {(c["action"], c["target"]) for c in past} if isinstance(past, list) else set()
    valid = [c for c in changes if isinstance(c, dict) and c.get("action") in ORDER]
    out = {"applied": 0, "pending": 0, "skipped": 0,
           "refused": [{"change": str(c)[:80], "why": "unknown action"}
                       for c in changes if c not in valid]}
    for ch in sorted(valid, key=lambda c: ORDER.index(c["action"]))[:MAX_CHANGES]:
        outcome, refusal = post_change(api, ch, evidence, done)
        if refusal:
            out["refused"].append(refusal)
        else:
            out[outcome] += 1
    out["summary"] = summary(evidence["task"], out)
    return out
