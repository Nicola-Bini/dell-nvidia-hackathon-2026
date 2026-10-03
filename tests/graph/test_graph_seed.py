"""PRD Flow 0 acceptance: what `make seed` leaves in the graph.

Public facts are read as cac_serve from kg_public; private ones as cac_owner from kg.
"""

import pytest

CATALOG_KEYS = {
    "component", "version", "use_when", "binds", "selectable", "preset", "cta_label",
    "rail_label", "say", "chips", "channels", "primitive", "fields", "submit_label",
}  # fmt: skip


def _count(conn, label: str) -> int:
    sql = "SELECT count(*) FROM kg_public.node WHERE label = %s"
    return conn.execute(sql, (label,)).fetchone()[0]


def _edges(conn, src: str, edge_type: str) -> list[tuple]:
    sql = "SELECT dst, props, verified_by_owner FROM kg_public.edge WHERE src = %s AND type = %s"
    return conn.execute(sql, (src, edge_type)).fetchall()


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Business", 1), ("Location", 1), ("HoursSpec", 3), ("SpecialHours", 2),
        ("MenuSection", 13), ("MenuItem", 110), ("Diet", 3), ("Allergen", 9), ("Service", 4),
        ("FAQ", 15), ("BrandTrait", 4), ("UIComponent", 10), ("Goal", 0), ("Customer", 0),
    ],
)  # fmt: skip
def test_published_node_counts(serve_conn, label, expected):
    assert _count(serve_conn, label) == expected


def test_flow0_minimums(serve_conn):
    assert _count(serve_conn, "MenuItem") >= 20
    assert _count(serve_conn, "HoursSpec") == 3
    assert _count(serve_conn, "Service") >= 2


def test_special_hours_dates_are_strings(serve_conn):
    rows = serve_conn.execute(
        "SELECT props -> 'date', jsonb_typeof(props -> 'date') FROM kg_public.node"
        " WHERE label = 'SpecialHours' ORDER BY id"
    ).fetchall()
    assert rows == [("2026-11-26", "string"), ("2027-07-04", "string")]


def test_hours_have_readable_names(serve_conn):
    rows = serve_conn.execute(
        "SELECT id, name FROM kg_public.node WHERE label = 'HoursSpec' ORDER BY id"
    ).fetchall()
    assert dict(rows) == {
        "hrs_sun": "Opening hours: Sunday",
        "hrs_mon_wed": "Opening hours: Monday to Wednesday",
        "hrs_thu_sat": "Opening hours: Thursday to Saturday",
    }


def test_no_goal_and_no_advances_in_public(serve_conn):
    assert _count(serve_conn, "Goal") == 0
    sql = "SELECT count(*) FROM kg_public.edge WHERE type = 'ADVANCES'"
    assert serve_conn.execute(sql).fetchone()[0] == 0


def test_exactly_two_components_carry_steer(serve_conn):
    rows = serve_conn.execute(
        "SELECT id, (props ->> 'steer')::int FROM kg_public.node WHERE props ? 'steer'"
    ).fetchall()
    assert dict(rows) == {"ui_booking_form": 5, "ui_catering_quote_form": 4}
    labels = serve_conn.execute(
        "SELECT DISTINCT label FROM kg_public.node WHERE props ? 'steer'"
    ).fetchall()
    assert labels == [("UIComponent",)]


def test_goals_are_private_approved_and_owner_verified(owner_conn, business_id):
    rows = owner_conn.execute(
        "SELECT id, visibility, status, verified_by_owner, props FROM kg.node"
        " WHERE label = 'Goal' AND business_id = %s ORDER BY id",
        (business_id,),
    ).fetchall()
    assert [r[:4] for r in rows] == [
        ("goal_bookings", "private", "approved", True),
        ("goal_catering", "private", "approved", True),
    ]
    assert rows[0][4] == {"statement": "Fill tables on weeknights", "priority": 5}
    edges = owner_conn.execute(
        "SELECT src, dst, status, verified_by_owner FROM kg.edge WHERE type = 'ADVANCES'"
        " ORDER BY src"
    ).fetchall()
    assert edges == [
        ("ui_booking_form", "goal_bookings", "approved", True),
        ("ui_catering_quote_form", "goal_catering", "approved", True),
    ]


def test_ref_item_has_two_has_item_edges_and_one_node(serve_conn):
    rows = serve_conn.execute(
        "SELECT src FROM kg_public.edge WHERE dst = 'mi_guinness' AND type = 'HAS_ITEM'"
        " ORDER BY src"
    ).fetchall()
    assert rows == [("sec_draft_beer",), ("sec_porters_stouts",)]
    total = serve_conn.execute(
        "SELECT count(*) FROM kg_public.edge WHERE type = 'HAS_ITEM'"
    ).fetchone()[0]
    assert total == 121


def test_has_item_position_is_the_order_within_the_section(serve_conn):
    draft = _edges(serve_conn, "sec_draft_beer", "HAS_ITEM")
    assert sorted(e[1]["position"] for e in draft) == list(range(1, 15))
    by_dst = {e[0]: e[1]["position"] for e in draft}
    assert by_dst["mi_bentwater_sluice_juice"] == 1
    assert by_dst["mi_guinness"] == 12
    stouts = _edges(serve_conn, "sec_porters_stouts", "HAS_ITEM")
    assert [(e[0], e[1]) for e in stouts] == [("mi_guinness", {"position": 1})]


def test_sections_are_positioned_in_file_order(serve_conn):
    rows = serve_conn.execute(
        "SELECT id, (props ->> 'position')::int FROM kg_public.node"
        " WHERE label = 'MenuSection' ORDER BY 2"
    ).fetchall()
    assert rows[0] == ("sec_draft_beer", 1)
    assert rows[-1] == ("sec_appetizers_salads", 13)
    assert [r[1] for r in rows] == list(range(1, 14))


def test_menu_items_have_currency_price_and_availability(serve_conn):
    props = serve_conn.execute(
        "SELECT props FROM kg_public.node WHERE id = 'mi_guinness'"
    ).fetchone()[0]
    assert props["price_cents"] == 900
    assert props["currency"] == "USD"
    assert props["available"] is True
    assert props["description"].startswith("Rich and creamy.")
    missing = serve_conn.execute(
        "SELECT count(*) FROM kg_public.node WHERE label = 'MenuItem'"
        " AND NOT (props ?& array['price_cents', 'currency', 'available'])"
    ).fetchone()[0]
    assert missing == 0


def test_verified_diet_edge_wins_over_the_unverified_one(serve_conn):
    burger = _edges(serve_conn, "mi_the_beyond_meat_burger_vegetarian", "SUITABLE_FOR")
    assert burger == [("diet_vegetarian", {}, True)]
    veg_dog = _edges(serve_conn, "mi_the_veg_dog", "SUITABLE_FOR")
    assert veg_dog == [("diet_vegetarian", {}, False)]
    total = serve_conn.execute(
        "SELECT count(*), count(*) FILTER (WHERE verified_by_owner) FROM kg_public.edge"
        " WHERE type = 'SUITABLE_FOR'"
    ).fetchone()
    assert total == (5, 1)


def test_verified_edge_has_verified_at_in_kg(owner_conn):
    rows = owner_conn.execute(
        "SELECT dst, verified_by_owner, verified_at IS NOT NULL FROM kg.edge"
        " WHERE type = 'SUITABLE_FOR'"
        " AND src IN ('mi_the_beyond_meat_burger_vegetarian', 'mi_the_veg_dog') ORDER BY src"
    ).fetchall()
    assert rows == [("diet_vegetarian", True, True), ("diet_vegetarian", False, False)]


def test_business_edges(serve_conn, business_id):
    counts = dict(
        serve_conn.execute(
            "SELECT type, count(*) FROM kg_public.edge WHERE src = %s GROUP BY type",
            (business_id,),
        ).fetchall()
    )
    assert counts == {"HAS_LOCATION": 1, "HAS_HOURS": 5, "HAS_SECTION": 13, "OFFERS": 4}
    answers = serve_conn.execute(
        "SELECT dst FROM kg_public.edge WHERE src = 'faq_catering' AND type = 'ANSWERS'"
    ).fetchall()
    assert answers == [("svc_catering",)]
    total = serve_conn.execute(
        "SELECT count(*) FROM kg_public.edge WHERE type = 'ANSWERS'"
    ).fetchone()[0]
    assert total == 15


def test_every_ui_component_has_every_catalog_key(serve_conn):
    rows = serve_conn.execute(
        "SELECT id, props FROM kg_public.node WHERE label = 'UIComponent'"
    ).fetchall()
    assert len(rows) == 10
    for node_id, props in rows:
        assert CATALOG_KEYS <= set(props), f"{node_id} lacks {CATALOG_KEYS - set(props)}"
        assert set(props) - CATALOG_KEYS <= {"steer"}, node_id
    by_id = dict(rows)
    assert by_id["ui_goal_cta"]["preset"] is None
    assert by_id["ui_goal_cta"]["rail_label"] is None
    assert by_id["ui_booking_form"]["cta_label"] == "Book a table"
    assert by_id["ui_form_contact"]["primitive"] == "FormCard"
    assert by_id["ui_form_contact"]["submit_label"] == "Send"
    assert len(by_id["ui_form_contact"]["fields"]) == 5


def test_ui_component_names(serve_conn):
    rows = dict(
        serve_conn.execute(
            "SELECT id, name FROM kg_public.node WHERE label = 'UIComponent'"
        ).fetchall()
    )
    assert rows["ui_booking_form"] == "Booking"
    assert rows["ui_goal_cta"] == "GoalCTA"


def test_business_has_nav_and_chips(serve_conn, business_id):
    name, props = serve_conn.execute(
        "SELECT name, props FROM kg_public.node WHERE id = %s", (business_id,)
    ).fetchone()
    assert name == "The Kenmore"
    assert props["nav"][0] == {"label": "Menu", "preset": "menu"}
    assert len(props["nav"]) == 4
    assert props["chips"] == ["What's on draft?", "Vegetarian options", "Are you open tonight?"]
    assert props["timezone"] == "America/New_York"
    assert props["cuisine"] == ["American Pub"]


def test_brand_traits_keep_kind_and_value(serve_conn):
    props = serve_conn.execute(
        "SELECT props FROM kg_public.node WHERE id = 'trait_color_background'"
    ).fetchone()[0]
    assert props == {"kind": "color", "value": "#111111"}


def test_diet_search_text_contains_its_synonyms(serve_conn):
    text = serve_conn.execute(
        "SELECT search_text FROM kg_public.node WHERE id = 'diet_gluten_free'"
    ).fetchone()[0]
    assert text.startswith("Gluten-free")
    for synonym in ("gf", "gluten free", "no gluten", "celiac", "coeliac"):
        assert synonym in text


def test_every_public_node_has_search_text(serve_conn):
    empty = serve_conn.execute(
        "SELECT count(*) FROM kg_public.node WHERE search_text = ''"
    ).fetchone()[0]
    assert empty == 0


def test_seeded_nodes_are_approved_seed_rows(owner_conn, business_id):
    rows = owner_conn.execute(
        "SELECT DISTINCT status, source_type FROM kg.node WHERE business_id = %s"
        " AND label <> 'KnowledgeGap' AND source_type = 'seed'",
        (business_id,),
    ).fetchall()
    assert rows == [("approved", "seed")]
    url = owner_conn.execute(
        "SELECT source_url FROM kg.node WHERE id = 'faq_kitchen_hours'"
    ).fetchone()[0]
    assert url == "https://www.thekenmorebar.com/location/the-kenmore/"


def test_registries_match_schema_sections_5_and_6(owner_conn):
    labels = dict(
        owner_conn.execute("SELECT label, (may_be_public, locked) FROM kg.label").fetchall()
    )
    locked = {name for name, (_, is_locked) in labels.items() if is_locked == "t"}
    private = {name for name, (public, _) in labels.items() if public == "f"}
    assert locked == private == {"Goal", "KnowledgeGap", "Customer", "Proposal", "OwnerNote"}
    assert len(labels) >= 22
    props = dict(owner_conn.execute("SELECT label, public_props FROM kg.label").fetchall())
    assert props["MenuItem"] == ["description", "price_cents", "currency", "available"]
    assert props["Business"][-2:] == ["nav", "chips"]
    assert set(props["UIComponent"]) == CATALOG_KEYS
    edge_props = dict(owner_conn.execute("SELECT type, public_props FROM kg.edge_type").fetchall())
    assert len(edge_props) >= 14
    assert edge_props["HAS_ITEM"] == ["position"]
    assert edge_props["RENDERS_WITH"] == ["weight"]
    assert edge_props["ADVANCES"] == []
