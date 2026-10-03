"""SCHEMA section 6: entry lookup, fixed expansions and the candidate cap.

The expansion tests on `example_graph` are pure. The rest read the seeded kg_public as
cac_serve (`make db-up seed`), with no embedder, so they exercise the full-text fallback.
"""

from __future__ import annotations

from datetime import date

import pytest

from cac_serve.domain import retrieve as retrieve_module
from cac_serve.domain.graph import Edge, Node
from cac_serve.domain.retrieve import CANDIDATE_CAP, candidates_from, expand, retrieve
from cac_serve.domain.slots import extract_slots
from cac_serve.infra import search_repo

TODAY = date(2026, 10, 3)
HOURS = {"hrs_sun", "hrs_mon_wed", "hrs_thu_sat", "sh_2026_11_26", "sh_2027_07_04"}


def _retrieve(conn, graph, text: str) -> list[str]:
    return retrieve(conn, graph, text, extract_slots(text, TODAY))


def _labels(graph, ids) -> set[str]:
    return {graph.get(i).label for i in ids}


# --- expansions, pure -----------------------------------------------------------------


def test_diet_expands_to_its_items_verified_first_then_their_sections(example_graph):
    assert expand(example_graph, "diet_vegetarian") == [
        "mi_mushroom_risotto", "mi_caprese", "sec_mains", "sec_desserts"]


def test_allergen_expands_only_over_owner_verified_edges(example_graph):
    assert expand(example_graph, "alg_peanuts") == ["mi_caprese"]


def test_item_expands_to_section_diets_and_verified_allergens(example_graph):
    assert expand(example_graph, "mi_caprese") == [
        "sec_desserts", "diet_vegetarian", "alg_peanuts"]
    assert expand(example_graph, "mi_ribeye") == ["sec_mains"]


def test_section_service_hours_and_faq_templates(example_graph):
    assert expand(example_graph, "sec_mains") == ["mi_mushroom_risotto", "mi_ribeye"]
    assert expand(example_graph, "svc_private_events") == ["faq_gluten_free_pasta"]
    assert expand(example_graph, "hrs_all") == ["hrs_all", "sh_2026_11_26"]
    assert expand(example_graph, "faq_parking") == []
    assert expand(example_graph, "ui_form_gift_card") == []


def test_unknown_label_gets_one_hop_without_catalog_or_brand_nodes(example_graph):
    assert candidates_from(example_graph, ["gc_standard"]) == [
        "gc_standard", "ui_form_gift_card", "biz_x"]


def test_entries_come_first_and_nothing_repeats(example_graph):
    ids = candidates_from(example_graph, ["faq_parking", "sec_mains", "faq_parking", "mi_gone"])
    assert ids == ["faq_parking", "sec_mains", "mi_mushroom_risotto", "mi_ribeye"]


def test_plain_catalog_entries_and_brand_traits_are_never_candidates(example_graph):
    assert candidates_from(example_graph, ["ui_menu_list", "trait_color", "ui_goal_cta"]) == []


def test_candidates_are_capped(example_graph):
    extra = [Node(f"mi_n{i:02d}", "MenuItem", f"Dish {i}", {}) for i in range(60)]
    edges = [Edge("sec_mains", n.id, "HAS_ITEM") for n in extra]
    ids = candidates_from(example_graph.extended(extra, edges), ["sec_mains"])
    assert len(ids) == CANDIDATE_CAP == 40
    assert ids[0] == "sec_mains"


def test_tokens_are_sanitized_before_they_reach_sql():
    assert search_repo.sanitize_tokens(["Guinness'; DROP--", "a|b", "ok", "ok"]) == [
        "guinness", "drop", "a", "b", "ok"]


# --- seeded graph ---------------------------------------------------------------------


def test_seeded_diet_expansion_has_items_and_sections(graph):
    ids = candidates_from(graph, ["diet_vegetarian"])
    assert ids[:2] == ["diet_vegetarian", "mi_the_beyond_meat_burger_vegetarian"]
    assert {"mi_the_veg_dog", "sec_burgers", "sec_hot_dogs"} <= set(ids)


def test_seeded_section_expansion_is_its_items(graph):
    ids = candidates_from(graph, ["sec_hot_dogs"])
    assert "mi_the_veg_dog" in ids
    assert _labels(graph, ids[1:]) == {"MenuItem"}


def test_seeded_service_expansion_is_its_faqs(graph):
    assert candidates_from(graph, ["svc_takeout"]) == ["svc_takeout", "faq_takeout_delivery"]


def test_seeded_hours_expansion_is_every_hours_node(graph):
    assert set(candidates_from(graph, ["hrs_sun"])) == HOURS


def test_agent_created_label_expands_one_hop_on_the_seeded_graph(graph):
    card = Node("gc_standard", "GiftCard", "Gift card", {"amounts": [25, 50]})
    extended = graph.extended([card], [Edge("biz_demo", "gc_standard", "SELLS")])
    assert candidates_from(extended, ["gc_standard"]) == ["gc_standard", "biz_demo"]


SMOKE = [
    ("vegetarian options", "diet_vegetarian"),
    ("I want to pick up something vegetarian", "diet_vegetarian"),
    ("what burgers do you have?", "sec_burgers"),
    ("show me the hot dogs", "sec_hot_dogs"),
    ("what's on draft?", "sec_draft_beer"),
    ("which IPAs do you have", "sec_ipas"),
    ("any sour beers?", "sec_sours"),
    ("do you have cocktails", "sec_cocktails"),
    ("red wine by the glass", "sec_red_wine"),
    ("do you have Guinness?", "mi_guinness"),
    ("do you have guiness", "mi_guinness"),
    ("how much are the chicken wings", "mi_chicken_wings"),
    ("what's in the Shroom Lover burger", "mi_shroom_lover_burger"),
    ("is the veg dog vegetarian?", "mi_the_veg_dog"),
    ("I'm allergic to peanuts", "alg_peanuts"),
    ("when does the kitchen close?", "faq_kitchen_hours"),
    ("do you do brunch?", "faq_brunch"),
    ("can I get delivery?", "faq_takeout_delivery"),
    ("can I add bacon to my burger?", "faq_burger_adds_sides"),
    ("can I host a birthday party there?", "faq_private_events"),
    ("is there a gluten free beer?", "diet_gluten_free"),
    ("I'd like to send you a message", "ui_form_contact"),
    ("table for 4 on Friday at 7pm", "svc_reservations"),
    ("do you cater for 40?", "svc_catering"),
]


@pytest.mark.parametrize(("text", "expected"), SMOKE)
def test_intent_retrieves_its_node(serve_conn, graph, text, expected):
    assert expected in _retrieve(serve_conn, graph, text)


@pytest.mark.parametrize(
    ("text", "first"),
    [("what's on draft?", "sec_draft_beer"), ("do you have Guinness?", "mi_guinness"),
     ("which IPAs do you have", "sec_ipas"), ("vegetarian options", "diet_vegetarian"),
     ("how much are the chicken wings", "mi_chicken_wings")],
)
def test_a_name_match_ranks_first(serve_conn, graph, text, first):
    assert _retrieve(serve_conn, graph, text)[0] == first


def test_nut_free_retrieves_an_allergen_and_no_menu(serve_conn, graph):
    ids = _retrieve(serve_conn, graph, "nut-free dishes")
    assert "Allergen" in _labels(graph, ids)
    assert not _labels(graph, ids) & {"MenuItem", "MenuSection", "Diet"}


def test_misspelt_words_still_find_their_node(serve_conn, graph):
    assert _retrieve(serve_conn, graph, "do you have guiness")[0] == "mi_guinness"
    assert "diet_vegetarian" in _retrieve(serve_conn, graph, "vegeterian food")


def test_business_node_is_an_entry_only_by_name(serve_conn, graph):
    # Its search_text holds the site's nav and chip text, and its one hop is most of the graph.
    for text in ("what's on draft?", "vegetarian options", "are you open tonight?"):
        ids = _retrieve(serve_conn, graph, text)
        assert "biz_demo" not in ids and len(ids) <= 20
    assert "biz_demo" in _retrieve(serve_conn, graph, "tell me about the kenmore")


def test_weak_matches_are_dropped_next_to_a_strong_one(serve_conn, graph):
    assert _retrieve(serve_conn, graph, "do you have Guinness?") == [
        "mi_guinness", "sec_draft_beer", "sec_porters_stouts"]
    assert _retrieve(serve_conn, graph, "I'm allergic to peanuts") == ["alg_peanuts"]


def test_off_topic_text_retrieves_nothing(serve_conn, graph):
    assert _retrieve(serve_conn, graph, "tell me a joke") == []
    assert _retrieve(serve_conn, graph, "") == []
    assert _retrieve(serve_conn, graph, "?!") == []


@pytest.mark.parametrize(
    "text",
    ["are you open tonight?", "what time do you close on Saturday",
     "are you open on the 4th of July?", "are you open on Thanksgiving?", "what are your hours"],
)
def test_hours_questions_bring_every_hours_node(serve_conn, graph, text):
    assert set(_retrieve(serve_conn, graph, text)) >= HOURS


@pytest.mark.parametrize("text", [t for t, _ in SMOKE] + ["menu", "beer", "the kenmore"])
def test_candidates_are_capped_unique_and_never_plain_catalog_entries(serve_conn, graph, text):
    ids = _retrieve(serve_conn, graph, text)
    assert len(ids) <= CANDIDATE_CAP
    assert len(ids) == len(set(ids))
    for node in map(graph.get, ids):
        assert node is not None and node.label != "BrandTrait"
        assert node.label != "UIComponent" or node.props.get("primitive") == "FormCard"


def test_hostile_text_is_only_ever_a_parameter(serve_conn, graph):
    text = "'); DROP TABLE kg_public.node; -- & | ! :* <-> guinness"
    assert "mi_guinness" in _retrieve(serve_conn, graph, text)
    assert serve_conn.execute("SELECT count(*) FROM kg_public.node").fetchone()[0] > 0


def test_search_works_without_pg_trgm(serve_conn, graph, monkeypatch):
    monkeypatch.setattr(search_repo, "has_trigrams", lambda conn: False)
    assert "mi_guinness" in _retrieve(serve_conn, graph, "do you have Guinness?")


def test_vector_path_is_used_when_an_embedder_answers(serve_conn, graph, monkeypatch):
    seen = {}

    def fake_vector_entries(conn, business_id, vector, limit, threshold):
        seen.update(vector=vector, limit=limit, threshold=threshold)
        return ["faq_brunch"]

    monkeypatch.setattr(retrieve_module, "_embedding", lambda text: [0.1] * 1024)
    monkeypatch.setattr(search_repo, "vector_entries", fake_vector_entries)
    assert _retrieve(serve_conn, graph, "anything at all") == ["faq_brunch"]
    assert seen["limit"] == 8 and seen["threshold"] == 0.35


def test_vector_sql_runs_and_falls_back_when_nothing_is_embedded(serve_conn, graph, monkeypatch):
    monkeypatch.setattr(retrieve_module, "_embedding", lambda text: [0.01] * 1024)
    embedded = serve_conn.execute(
        "SELECT count(*) FROM kg_public.node WHERE embedding IS NOT NULL").fetchone()[0]
    ids = _retrieve(serve_conn, graph, "do you have Guinness?")
    if embedded == 0:
        assert "mi_guinness" in ids
    assert len(ids) <= CANDIDATE_CAP
