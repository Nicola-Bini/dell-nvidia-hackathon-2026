"""Real Postgres 16 + pgvector (embedded), real db/schema.sql, a small fixture graph."""

import pathlib
import tempfile

import httpx
import psycopg
import pgserver
import pytest
from fastapi.testclient import TestClient

from cac_common.settings import Settings, load_settings
from app.main import create_app

SCHEMA = pathlib.Path(__file__).resolve().parents[3] / "db" / "schema.sql"
AGENT = {"Authorization": "Bearer agent-secret"}
OWNER = {"Authorization": "Bearer owner-secret"}

LABELS = [  # label, may_be_public, public_props, locked
    ("Business", True, ["cuisine", "phone", "tagline"], False),
    ("MenuSection", True, ["position"], False),
    ("MenuItem", True, ["description", "price_cents", "currency", "available"], False),
    ("Diet", True, ["schema_org", "synonyms"], False),
    ("Allergen", True, ["fda_major", "synonyms"], False),
    ("Service", True, ["kind", "details", "booking_url"], False),
    ("FAQ", True, ["question", "answer"], False),
    ("SpecialHours", True, ["date", "closed", "opens", "closes", "note"], False),
    ("UIComponent", True, ["component", "version", "use_when", "binds", "selectable", "preset",
                           "cta_label", "say", "chips", "channels", "primitive", "fields"], False),
    ("Note", False, [], False),
    ("Goal", False, [], True),
    ("KnowledgeGap", False, [], True),
    ("Customer", False, [], True),
    ("Proposal", False, [], True),
    ("OwnerNote", False, [], True),
]
EDGE_TYPES = [("HAS_SECTION", []), ("HAS_ITEM", ["position"]), ("SUITABLE_FOR", []),
              ("CONTAINS_ALLERGEN", []), ("OFFERS", []), ("ANSWERS", []), ("ADVANCES", []),
              ("ABOUT", []), ("PAIRS_WITH", []), ("HAS_HOURS", [])]
NODES = [  # id, label, name, props, visibility, status
    ("biz_demo", "Business", "The Kenmore", {"cuisine": "Pub", "supplier": "Sysco"}, "public"),
    ("mi_risotto", "MenuItem", "Mushroom Risotto",
     {"description": "Arborio rice, mushrooms", "price_cents": 1800, "margin": 0.62}, "public"),
    ("mi_caprese", "MenuItem", "Caprese", {"description": "Tomato, mozzarella"}, "public"),
    ("diet_vegan", "Diet", "Vegan", {"synonyms": ["plant-based"]}, "public"),
    ("diet_vegetarian", "Diet", "Vegetarian", {"synonyms": ["veggie"]}, "public"),
    ("svc_reservations", "Service", "Table requests", {"kind": "reservations"}, "public"),
    ("goal_bookings", "Goal", "More bookings", {"statement": "Fill weeknights", "priority": 5},
     "private"),
    ("cust_canary", "Customer", "ZZ-CANARY-Customer", {"contact": "canary@example.com"},
     "private"),
]


def serve_is_down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("serve api is not running in tests", request=request)


def make_settings(url: str, **kw) -> Settings:
    env = {"OWNER_DATABASE_URL": url, "OWNER_TOOLS_TOKEN": "agent-secret",
           "OWNER_INBOX_TOKEN": "owner-secret", "EMBED_BASE_URL": "",
           "SERVE_BASE_URL": "http://127.0.0.1:1", "CAC_AUTONOMY": "balanced"}
    if "autonomy" in kw:
        env["CAC_AUTONOMY"] = kw.pop("autonomy")
    env.update({k.upper(): str(v) for k, v in kw.items()})
    return load_settings(env)


@pytest.fixture(scope="session")
def pg():
    srv = pgserver.get_server(tempfile.mkdtemp(), cleanup_mode="stop")
    admin = srv.get_uri()
    ddl = SCHEMA.read_text(encoding="utf-8")
    ddl = ddl.replace(":'owner_pw'", "'ow'").replace(":'serve_pw'", "'sv'")
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(ddl)
    yield {"owner": admin.replace("postgres:@", "cac_owner:ow@"),
           "serve": admin.replace("postgres:@", "cac_serve:sv@"), "admin": admin}
    srv.cleanup()


def seed_graph(conn: psycopg.Connection) -> None:
    for label, pub, props, locked in LABELS:
        conn.execute("INSERT INTO kg.label (label, may_be_public, public_props, description,"
                     " locked) VALUES (%s, %s, %s, %s, %s)", (label, pub, props, label, locked))
    for etype, props in EDGE_TYPES:
        conn.execute("INSERT INTO kg.edge_type (type, public_props, description)"
                     " VALUES (%s, %s, %s)", (etype, props, etype))
    for nid, label, name, props, vis in NODES:
        conn.execute(
            "INSERT INTO kg.node (id, business_id, label, name, props, visibility, status,"
            " source_type, verified_by_owner, search_text) VALUES"
            " (%s, 'biz_demo', %s, %s, %s::jsonb, %s, 'approved', 'seed', true, %s)",
            (nid, label, name, psycopg.types.json.Jsonb(props), vis, name))
    conn.execute("INSERT INTO kg.edge (business_id, src, dst, type, status, source_type)"
                 " VALUES ('biz_demo', 'mi_caprese', 'diet_vegetarian', 'SUITABLE_FOR',"
                 " 'approved', 'seed')")
    conn.execute("SELECT kg.publish('biz_demo')")


@pytest.fixture()
def db(pg):
    """A clean database with the fixture graph. Yields a cac_owner connection."""
    with psycopg.connect(pg["admin"], autocommit=True) as admin:
        admin.execute("TRUNCATE kg.change, kg.edge, kg.node, kg.edge_type, kg.label, "
                      "kg_public.edge, kg_public.node, kg_public.meta, ops.intent_log, "
                      "ops.intent_cache, ops.lead, ops.sync_state RESTART IDENTITY CASCADE")
    with psycopg.connect(pg["owner"], row_factory=psycopg.rows.dict_row) as conn:
        seed_graph(conn)
        conn.commit()
        yield conn


@pytest.fixture()
def make_client(pg, db):
    def build(**kw) -> TestClient:
        app = create_app(make_settings(pg["owner"], **kw))
        app.state.serve_transport = httpx.MockTransport(serve_is_down)  # no real network
        return TestClient(app)
    return build


@pytest.fixture()
def client(make_client):
    return make_client()
