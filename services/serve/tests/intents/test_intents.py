"""wp4 proof: the 30 fixture intents (SCHEMA section 10).

Pass: 30 of 30 selections are schema-valid, at least 27 of 30 pick the expected component
and filter, and asking the same question twice makes one model call.
"""

from __future__ import annotations

import jsonschema
import pytest

pytestmark = pytest.mark.intents

REQUIRED_CORRECT = 27
VIEW_KEYS = ("diet", "section", "faq", "allergen", "form", "order")


def matches(expect: dict, selection: dict | None) -> bool:
    if selection is None:
        return False
    if "kind" in expect:
        return selection.get("kind") == expect["kind"]
    views = selection.get("views") or []
    if selection.get("kind") != "answer" or not views:
        return False
    view = views[0]
    if view.get("component") != expect["component"]:
        return False
    if any(key in expect and view.get(key) != expect[key] for key in VIEW_KEYS):
        return False
    return set(expect.get("items", [])) <= set(view.get("items", []))


def test_every_selection_is_schema_valid(intents, outcomes):
    invalid = []
    for row in intents:
        outcome = outcomes[row["text"]]
        try:
            jsonschema.validate(outcome.selection, outcome.schema)
        except jsonschema.ValidationError as exc:
            invalid.append((row["text"], exc.message))
    assert not invalid, invalid


def test_at_least_27_of_30_pick_the_right_component(intents, outcomes):
    assert len(intents) == 30
    wrong = [(row["text"], outcomes[row["text"]].selection)
             for row in intents if not matches(row["expect"], outcomes[row["text"]].selection)]
    correct = len(intents) - len(wrong)
    print(f"\nintents: {correct} of {len(intents)} correct")
    for text, selection in wrong:
        print(f"  wrong: {text!r} -> {selection}")
    assert correct >= REQUIRED_CORRECT, wrong


def test_same_question_twice_makes_one_model_call(intents_client, outcomes):
    client = intents_client
    question = {"text": "what cocktails do you have tonight?", "session_id": "intents-test"}
    before = client.get("/v1/metrics").json()["model_calls"]
    first = client.post("/v1/intent", json=question)
    second = client.post("/v1/intent", json=question)
    after = client.get("/v1/metrics").json()["model_calls"]
    assert first.status_code == second.status_code == 200
    assert first.json()["meta"]["cache"] == "miss"
    assert second.json()["meta"]["cache"] == "exact"
    assert after - before == 1
    assert first.json()["views"] == second.json()["views"]
