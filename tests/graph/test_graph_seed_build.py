"""The seed builder (scripts/seedlib), without a database."""

from pathlib import Path

import pytest
import yaml
from seedlib.build import build_graph, hours_name, snake_case

DEMO = Path(__file__).resolve().parents[2] / "demo" / "kenmore"


@pytest.fixture(scope="module")
def built():
    seed = yaml.safe_load((DEMO / "seed.yaml").read_text(encoding="utf-8"))
    overlay = yaml.safe_load((DEMO / "demo-overlay.yaml").read_text(encoding="utf-8"))
    return build_graph(seed, overlay)


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (["sun"], "Opening hours: Sunday"),
        (["mon", "tue", "wed"], "Opening hours: Monday to Wednesday"),
        (["thu", "fri", "sat"], "Opening hours: Thursday to Saturday"),
        (["mon", "wed"], "Opening hours: Monday, Wednesday"),
    ],
)
def test_hours_name(days, expected):
    assert hours_name(days) == expected


@pytest.mark.parametrize(
    ("component", "expected"),
    [("BookingForm", "booking_form"), ("CateringQuoteForm", "catering_quote_form"),
     ("GoalCTA", "goal_cta")],
)  # fmt: skip
def test_snake_case(component, expected):
    assert snake_case(component) == expected


def test_build_is_deterministic_and_complete(built):
    labels = [n.label for n in built.nodes.values()]
    assert labels.count("MenuItem") == 110
    assert labels.count("Goal") == 2
    assert labels.count("Customer") == 1
    assert len(built.nodes) == 178
    assert all(e.src in built.nodes and e.dst in built.nodes for e in built.edges.values())


def test_private_nodes_are_goals_and_the_canary_only(built):
    private = {n.id for n in built.nodes.values() if n.visibility == "private"}
    assert private == {"goal_bookings", "goal_catering", "cust_canary"}


def test_special_hours_date_is_a_string(built):
    assert built.nodes["sh_2026_11_26"].props["date"] == "2026-11-26"
    assert built.nodes["sh_2026_11_26"].name == "Thanksgiving"


def test_one_edge_per_item_and_diet_verified_wins(built):
    key = ("mi_the_beyond_meat_burger_vegetarian", "diet_vegetarian", "SUITABLE_FOR")
    assert built.edges[key].verified is True
    assert built.edges[("mi_the_veg_dog", "diet_vegetarian", "SUITABLE_FOR")].verified is False
