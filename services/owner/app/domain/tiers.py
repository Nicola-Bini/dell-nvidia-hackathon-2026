"""Approval tiers (SCHEMA section 8.6) as a pure function of the change and the graph state.

`classify` maps (action, target state, requested `after`) to one row of the tier table;
`assign_tier` reads the cell for the autonomy setting. Nothing here touches the database.
"""

from dataclasses import dataclass, field
from enum import StrEnum

ACTIONS = (
    "create_label", "add_prop", "create_edge_type",
    "create_node", "update_node", "retire_node",
    "create_edge", "retire_edge",
    "create_component", "update_component",
)
AUTONOMY = ("cautious", "balanced", "free")
LOCKED_LABELS = ("Goal", "KnowledgeGap", "Customer", "Proposal", "OwnerNote")
UNVERIFIED_TAG_TYPES = ("SUITABLE_FOR", "CONTAINS_ALLERGEN")
VERIFY_FIELDS = ("verified_by_owner", "verified_at")


class Kind(StrEnum):
    """One row of the SCHEMA 8.6 tier table."""

    PRIVATE = "stays private"
    UNVERIFIED_TAG = "tag with its own 'not verified' marker"
    PUBLIC_LINK = "link between existing public nodes"
    NEW_PUBLIC_NODE = "new node of a public label"
    PUBLIC_EDIT = "edit of an existing public fact"
    NEW_STRUCTURE = "new public label, public prop or edge type"
    ELEMENT = "new or changed element"
    SET_VERIFIED = "setting verified_by_owner"
    LOCKED_DATA = "locked label, leads or visitor text"
    MAKE_PUBLIC = "making a private label public or unlocking it"


TABLE: dict[Kind, tuple[str, str, str]] = {  # (cautious, balanced, free)
    Kind.PRIVATE: ("auto", "auto", "auto"),
    Kind.UNVERIFIED_TAG: ("one_tap", "auto", "auto"),
    Kind.PUBLIC_LINK: ("one_tap", "auto", "auto"),
    Kind.NEW_PUBLIC_NODE: ("one_tap", "one_tap", "auto"),
    Kind.PUBLIC_EDIT: ("one_tap", "one_tap", "auto"),
    Kind.NEW_STRUCTURE: ("one_tap", "one_tap", "auto"),
    Kind.ELEMENT: ("one_tap", "one_tap", "auto"),
    Kind.SET_VERIFIED: ("locked", "locked", "locked"),
    Kind.LOCKED_DATA: ("locked", "locked", "locked"),
    Kind.MAKE_PUBLIC: ("locked", "locked", "locked"),
}

REASONS = {
    Kind.SET_VERIFIED: "Only the owner can mark something verified (POST /owner/verify).",
    Kind.LOCKED_DATA: "Goals, gaps, customers, proposals, owner notes, leads and visitor "
                      "text are locked: the agent cannot read or write them.",
    Kind.MAKE_PUBLIC: "Only the owner can make a private label public or unlock a label.",
}


@dataclass(frozen=True)
class NodeState:
    """What the tier rules need to know about one node."""

    label: str
    label_public: bool  # kg.label.may_be_public
    visibility: str = "public"
    locked: bool = False

    @property
    def public(self) -> bool:
        return self.label_public and self.visibility == "public" and not self.locked


@dataclass(frozen=True)
class TargetState:
    """Current state of the change's target, read from `kg` by the caller."""

    label: str | None = None
    label_exists: bool = False
    label_public: bool = False
    label_locked: bool = False
    node: NodeState | None = None          # node actions: the node (or the new one)
    src: NodeState | None = None           # edge actions
    dst: NodeState | None = None
    edge_type: str | None = None
    edge_verified: bool = False
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TierDecision:
    tier: str
    kind: Kind
    reason: str


def assign_tier(action: str, state: TargetState, after: dict, autonomy: str) -> TierDecision:
    """Return the tier for a change. Pure: same inputs, same answer."""
    if autonomy not in AUTONOMY:
        autonomy = "balanced"
    kind = classify(action, state, after)
    tier = TABLE[kind][AUTONOMY.index(autonomy)]
    reason = REASONS.get(kind, f"{kind.value}: {tier} under '{autonomy}' autonomy.")
    return TierDecision(tier=tier, kind=kind, reason=reason)


def classify(action: str, state: TargetState, after: dict) -> Kind:
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action!r}")
    if _sets_verified(after):
        return Kind.SET_VERIFIED
    handler = _HANDLERS[action]
    return handler(state, after)


def _sets_verified(after: dict) -> bool:
    if any(after.get(f) for f in VERIFY_FIELDS):
        return True
    props = after.get("props")
    return isinstance(props, dict) and any(props.get(f) for f in VERIFY_FIELDS)


def is_locked_label(name: str | None) -> bool:
    return bool(name) and name.lower() in {x.lower() for x in LOCKED_LABELS}


def _create_label(state: TargetState, after: dict) -> Kind:
    if is_locked_label(state.label) or state.label_locked:
        return Kind.MAKE_PUBLIC if after.get("locked") is False else Kind.LOCKED_DATA
    if state.label_exists and not state.label_public and after.get("may_be_public"):
        return Kind.MAKE_PUBLIC
    return Kind.NEW_STRUCTURE if after.get("may_be_public") else Kind.PRIVATE


def _add_prop(state: TargetState, after: dict) -> Kind:
    if is_locked_label(state.label) or state.label_locked:
        return Kind.LOCKED_DATA
    if after.get("may_be_public") and not state.label_public:
        return Kind.MAKE_PUBLIC
    return Kind.NEW_STRUCTURE if state.label_public else Kind.PRIVATE


def _create_edge_type(state: TargetState, after: dict) -> Kind:
    return Kind.NEW_STRUCTURE


def _node_locked(node: NodeState | None, state: TargetState) -> bool:
    if node is None:
        return is_locked_label(state.label) or state.label_locked
    return node.locked or is_locked_label(node.label)


def _create_node(state: TargetState, after: dict) -> Kind:
    if _node_locked(state.node, state):
        return Kind.LOCKED_DATA
    wants_public = after.get("visibility", "public") == "public"
    return Kind.NEW_PUBLIC_NODE if state.label_public and wants_public else Kind.PRIVATE


def _update_node(state: TargetState, after: dict) -> Kind:
    node = state.node
    if _node_locked(node, state):
        return Kind.LOCKED_DATA
    if node is None:
        return Kind.PRIVATE
    if node.public:
        return Kind.PUBLIC_EDIT
    if node.label_public and after.get("visibility") == "public":
        return Kind.NEW_PUBLIC_NODE
    return Kind.PRIVATE


def _retire_node(state: TargetState, after: dict) -> Kind:
    node = state.node
    if _node_locked(node, state):
        return Kind.LOCKED_DATA
    return Kind.PUBLIC_EDIT if node is not None and node.public else Kind.PRIVATE


def _edge_kind(state: TargetState) -> Kind:
    ends = (state.src, state.dst)
    if any(n is not None and (n.locked or is_locked_label(n.label)) for n in ends):
        return Kind.LOCKED_DATA
    if not all(n is not None and n.public for n in ends):
        return Kind.PRIVATE
    if state.edge_type in UNVERIFIED_TAG_TYPES:
        return Kind.UNVERIFIED_TAG
    return Kind.PUBLIC_LINK


def _create_edge(state: TargetState, after: dict) -> Kind:
    return _edge_kind(state)


def _retire_edge(state: TargetState, after: dict) -> Kind:
    kind = _edge_kind(state)
    if kind in (Kind.UNVERIFIED_TAG, Kind.PUBLIC_LINK) and state.edge_verified:
        return Kind.PUBLIC_EDIT  # removing an owner-verified fact is an edit of that fact
    return kind


def _component(state: TargetState, after: dict) -> Kind:
    return Kind.ELEMENT


_HANDLERS = {
    "create_label": _create_label,
    "add_prop": _add_prop,
    "create_edge_type": _create_edge_type,
    "create_node": _create_node,
    "update_node": _update_node,
    "retire_node": _retire_node,
    "create_edge": _create_edge,
    "retire_edge": _retire_edge,
    "create_component": _component,
    "update_component": _component,
}
