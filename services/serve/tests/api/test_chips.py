"""Every chip the Serve API suggests must resolve when the widget sends it back as text."""

from __future__ import annotations

import pytest


def _ask(client, text: str) -> dict:
    response = client.post("/v1/intent", json={"text": text, "session_id": "chips"})
    assert response.status_code == 200
    return response.json()


def _model_calls(client) -> int:
    return client.get("/v1/metrics").json()["model_calls"]


@pytest.mark.parametrize("text", ["See the menu", "show me the menu", "Menu",
                                  "what's on the menu?", "can I see your full menu please"])
def test_whole_menu_ask_is_the_menu_preset_with_no_model_call(client, text):
    surface = _ask(client, text)
    assert (surface["kind"], surface["meta"]["cache"]) == ("preset", "preset")
    assert sum(view["component"] == "MenuList" for view in surface["views"]) == 13
    assert _model_calls(client) == 0


@pytest.mark.parametrize(("text", "component"), [
    ("Book a table", "BookingForm"), ("Get a catering quote", "CateringQuoteForm"),
    ("Hours", "HoursCard"), ("Catering", "CateringQuoteForm")])
def test_goal_and_nav_labels_open_their_preset(client, text, component):
    surface = _ask(client, text)
    assert surface["kind"] == "preset"
    assert surface["views"][0]["component"] == component
    assert _model_calls(client) == 0


def test_a_menu_question_still_goes_to_the_pipeline(client):
    surface = _ask(client, "what's on draft?")
    assert surface["kind"] == "answer"
    assert surface["title"] == "Draft Beer"


def test_every_suggested_chip_resolves(client, graph):
    """No chip in the catalog or the bootstrap leads to a gap or the off-topic surface."""
    chips = set(graph.business().props["chips"])
    for entry in graph.catalog():
        chips.update(entry.props.get("chips") or [])
    unresolved = [chip for chip in sorted(chips)
                  if _ask(client, chip)["kind"] not in ("answer", "preset")]
    assert unresolved == []
