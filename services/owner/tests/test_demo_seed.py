"""wp6: the pre-demo traffic makes /owner/gaps and /owner/topics show parking and gift cards."""

from app.demo import seed_traffic
from tests.conftest import AGENT
from tests.test_change_engine import scalar


def test_seeding_makes_both_topics_appear(client, db):
    result = seed_traffic.seed(db, "biz_demo")
    db.commit()
    assert result["parking"] == 5 and result["gift cards"] == 12

    gaps = client.get("/owner/gaps", headers=AGENT).json()
    assert [(g["topic"], g["count"]) for g in gaps] == [("gift cards", 12), ("parking", 5)]

    topics = {t["topic"]: t for t in client.get("/owner/topics", headers=AGENT).json()
              if t["kind"] == "gap"}
    assert topics["parking"]["sessions"] == 5 and topics["gift cards"]["sessions"] == 12


def test_seeding_twice_does_not_double_the_traffic(client, db):
    seed_traffic.seed(db, "biz_demo")
    seed_traffic.seed(db, "biz_demo")
    db.commit()
    gaps = {g["topic"]: g["count"] for g in client.get("/owner/gaps", headers=AGENT).json()}
    assert gaps == {"gift cards": 12, "parking": 5}


def test_reset_removes_only_the_seeded_rows(client, db):
    db.execute("INSERT INTO ops.intent_log (business_id, channel, session_id, text, cache,"
               " kind, latency_ms, graph_version) VALUES ('biz_demo', 'web', 'real-1', 'hi',"
               " 'miss', 'off_topic', 3, 1)")
    seed_traffic.seed(db, "biz_demo")
    removed = seed_traffic.reset(db, "biz_demo")
    db.commit()
    assert removed > 0
    assert scalar(db, "SELECT count(*) FROM ops.intent_log") == 1


def test_seeded_rows_are_marked_and_dated_today(db):
    seed_traffic.seed(db, "biz_demo")
    db.commit()
    assert scalar(db, "SELECT count(*) FROM ops.intent_log"
                  " WHERE session_id NOT LIKE 'demo-%%'") == 0
    assert scalar(db, "SELECT count(*) FROM ops.intent_log WHERE ts > now() - interval '2 hours'"
                  ) > 0
