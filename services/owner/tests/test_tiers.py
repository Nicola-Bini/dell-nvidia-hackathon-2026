"""One test per cell of the SCHEMA 8.6 tier table (10 rows x 3 autonomy settings)."""

import pytest

from app.domain.tiers import Kind, NodeState, TargetState, assign_tier

PUB = NodeState(label="MenuItem", label_public=True)
VEGAN = NodeState(label="Diet", label_public=True)
PRIV = NodeState(label="Note", label_public=False, visibility="private")
GOAL = NodeState(label="Goal", label_public=False, locked=True)

# row -> (action, state, after, edge-type-aware expected kind)
ROWS = {
    Kind.PRIVATE: ("create_node", TargetState(label="Note", node=None), {"visibility": "private"}),
    Kind.UNVERIFIED_TAG: ("create_edge", TargetState(src=PUB, dst=VEGAN,
                                                     edge_type="SUITABLE_FOR"), {}),
    Kind.PUBLIC_LINK: ("create_edge", TargetState(src=PUB, dst=PUB, edge_type="PAIRS_WITH"), {}),
    Kind.NEW_PUBLIC_NODE: ("create_node", TargetState(label="FAQ", label_public=True),
                           {"name": "x"}),
    Kind.PUBLIC_EDIT: ("update_node", TargetState(node=PUB), {"props": {"description": "new"}}),
    Kind.NEW_STRUCTURE: ("create_label", TargetState(label="GiftCard"), {"may_be_public": True}),
    Kind.ELEMENT: ("create_component", TargetState(), {"primitive": "FormCard"}),
    Kind.SET_VERIFIED: ("update_node", TargetState(node=PUB), {"verified_by_owner": True}),
    Kind.LOCKED_DATA: ("update_node", TargetState(node=GOAL), {"props": {"statement": "x"}}),
    Kind.MAKE_PUBLIC: ("create_label", TargetState(label="Note", label_exists=True,
                                                   label_public=False), {"may_be_public": True}),
}

EXPECTED = {  # (cautious, balanced, free), copied from the SCHEMA 8.6 table
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

CELLS = [(kind, mode, EXPECTED[kind][i])
         for kind in EXPECTED for i, mode in enumerate(("cautious", "balanced", "free"))]


@pytest.mark.parametrize("kind,mode,tier", CELLS, ids=[f"{k.name}-{m}" for k, m, _ in CELLS])
def test_tier_cell(kind, mode, tier):
    action, state, after = ROWS[kind]
    decision = assign_tier(action, state, after, mode)
    assert decision.kind == kind
    assert decision.tier == tier


def test_unknown_autonomy_falls_back_to_balanced():
    action, state, after = ROWS[Kind.UNVERIFIED_TAG]
    assert assign_tier(action, state, after, "bogus").tier == "auto"


def test_unknown_action_is_rejected():
    with pytest.raises(ValueError):
        assign_tier("drop_table", TargetState(), {}, "free")


def test_locked_reasons_are_given():
    action, state, after = ROWS[Kind.LOCKED_DATA]
    assert "locked" in assign_tier(action, state, after, "free").reason


def test_verified_hidden_in_props_is_still_locked():
    d = assign_tier("create_node", TargetState(label="FAQ", label_public=True),
                    {"props": {"verified_by_owner": True}}, "free")
    assert d.tier == "locked"


def test_locked_label_name_cannot_be_created_by_agent():
    d = assign_tier("create_label", TargetState(label="goal"), {"may_be_public": False}, "free")
    assert d.tier == "locked"


def test_unlocking_a_label_is_locked():
    d = assign_tier("create_label", TargetState(label="Customer", label_exists=True,
                                                label_locked=True), {"locked": False}, "free")
    assert d.kind == Kind.MAKE_PUBLIC and d.tier == "locked"


def test_edge_touching_a_goal_is_locked():
    d = assign_tier("create_edge", TargetState(src=PUB, dst=GOAL, edge_type="ADVANCES"), {},
                    "free")
    assert d.tier == "locked"


def test_edge_between_private_nodes_stays_private():
    d = assign_tier("create_edge", TargetState(src=PRIV, dst=PUB, edge_type="PAIRS_WITH"), {},
                    "cautious")
    assert d.tier == "auto"


def test_private_node_edit_is_auto_in_every_mode():
    for mode in ("cautious", "balanced", "free"):
        assert assign_tier("update_node", TargetState(node=PRIV), {}, mode).tier == "auto"


def test_retire_public_node_is_an_edit_of_a_public_fact():
    assert assign_tier("retire_node", TargetState(node=PUB), {}, "balanced").tier == "one_tap"
