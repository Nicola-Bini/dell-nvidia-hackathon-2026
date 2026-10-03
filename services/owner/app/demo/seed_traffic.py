"""Insert the pre-demo visitor traffic (PRD section 15): 5 sessions asking about parking, a real
gap in the Kenmore data that stands in for the PRD's gluten-free pasta, and 12 asking about gift
cards. Rows go straight into `ops.intent_log` as the Serve API would have written them.

    uv run python -m app.demo.seed_traffic            # add the traffic (safe to repeat)
    uv run python -m app.demo.seed_traffic --reset    # remove it again

Every seeded row has a `demo-` session id, so `--reset` never touches real traffic.
"""

import argparse
import random
from collections.abc import Iterator

import psycopg
from cac_common.settings import get_settings
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

PREFIX = "demo-"
GAPS = {
    "parking": 5,
    "gift cards": 12,
}
PHRASES = {
    "parking": ["is there parking nearby?", "where can I park?", "do you have a parking lot",
                "is street parking free after 6", "any garage close to you guys?"],
    "gift cards": ["do you sell gift cards?", "can I buy a gift card", "gift certificates?",
                   "I want to get a gift card for my brother", "do you do gift cards online",
                   "how much are your gift cards", "can i give someone a gift card",
                   "gift card for a birthday?"],
}
BACKGROUND = [
    ("vegetarian options", "MenuList"), ("what's on draft?", "MenuList"),
    ("are you open tonight?", "HoursCard"), ("what time do you close on Saturday",
                                              "HoursCard"),
    ("table for 4 on Friday at 7pm", "BookingForm"), ("do you cater for 40?",
                                                       "CateringQuoteForm"),
]
ROW = ("INSERT INTO ops.intent_log (ts, business_id, channel, session_id, text, cache, kind,"
       " gap_topic, selection, latency_ms, model, graph_version) VALUES"
       " (now() - make_interval(mins => %s), %s, 'web', %s, %s, 'miss', %s, %s, %s, %s,"
       " 'seed', %s)")


def _rows(rng: random.Random) -> Iterator[tuple]:
    """(minutes_ago, session, text, kind, topic, selection, latency_ms)"""
    for topic, sessions in GAPS.items():
        for i in range(sessions):
            text = PHRASES[topic][i % len(PHRASES[topic])]
            yield (rng.randint(5, 90), f"{PREFIX}{topic.replace(' ', '-')}-{i + 1}", text, "gap",
                   topic, None, rng.randint(90, 400))
    for i, (text, component) in enumerate(BACKGROUND):
        yield (rng.randint(5, 90), f"{PREFIX}bg-{i + 1}", text, "answer", None,
               {"kind": "answer", "views": [{"component": component}]}, rng.randint(40, 300))


def reset(conn: psycopg.Connection, biz: str) -> int:
    return conn.execute("DELETE FROM ops.intent_log WHERE business_id = %s AND session_id"
                        " LIKE %s", (biz, f"{PREFIX}%")).rowcount


def seed(conn: psycopg.Connection, biz: str) -> dict:
    """Insert the traffic once. Returns the number of sessions per gap topic."""
    reset(conn, biz)
    meta = conn.execute("SELECT graph_version FROM kg_public.meta WHERE business_id = %s",
                        (biz,)).fetchone()
    version = meta["graph_version"] if meta else 1
    for minutes, session, text, kind, topic, selection, latency in _rows(random.Random(3)):
        conn.execute(ROW, (minutes, biz, session, text, kind, topic,
                           Jsonb(selection) if selection else None, latency, version))
    return dict(GAPS)


def main(argv: list[str] | None = None) -> int:
    args = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    args.add_argument("--reset", action="store_true", help="remove the seeded traffic")
    opts = args.parse_args(argv)
    settings = get_settings()
    with psycopg.connect(settings.owner_database_url, row_factory=dict_row) as conn:
        if opts.reset:
            print(f"removed {reset(conn, settings.business_id)} seeded rows")
        else:
            seed(conn, settings.business_id)
            print("seeded 5 parking sessions and 12 gift card sessions "
                  "(GET /owner/gaps and /owner/topics now show both)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
