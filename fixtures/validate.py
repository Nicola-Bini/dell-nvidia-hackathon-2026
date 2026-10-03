"""Validate the golden surfaces against the Kenmore demo data (seed + overlay + intents).

Run: uv run --with pyyaml python fixtures/validate.py   (exits non-zero on failure)
"""
import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo/kenmore"
SURFACES = ROOT / "fixtures/surfaces"
EXPECTED = {
    "allergen_peanuts", "answer_kitchen_hours", "booking_form", "busy_fallback",
    "catering_form_40", "fact_card", "form_contact", "gap", "gift_cards", "hours_july4",
    "hours_saturday", "menu_draft_beer", "menu_vegetarian", "menu_vegetarian_order",
    "off_topic", "preset_menu",
}
SURFACE_KEYS = {"surface_id", "kind", "title", "say", "views", "chips", "meta"}
VIEW_KEYS = {"id", "component", "data", "actions", "text"}
META_KEYS = {"cache", "latency_ms", "graph_version", "model"}
STEER = {"BookingForm", "CateringQuoteForm"}
ID_RE = re.compile(r"\b(?:mi|sec|diet|alg|faq|svc|ui|sh|hrs|loc|biz)_[a-z0-9_]+")
POST_AGENT = {"ui_form_gift_card"}          # allowed in gift_cards.json only
errors = []


def check(ok, msg):
    if not ok:
        errors.append(msg)


def load():
    """Apply seed.yaml, then demo-overlay.yaml; return (ids, items, components, verified)."""
    seed = yaml.safe_load((DEMO / "seed.yaml").read_text())
    over = yaml.safe_load((DEMO / "demo-overlay.yaml").read_text())
    ids = {seed["business"]["id"], seed["location"]["id"]}
    items = {}
    for sec in seed["sections"]:
        ids.add(sec["id"])
        items.update({i["id"]: i for i in sec["items"] if "id" in i})
    for sec in seed["sections"]:
        for i in sec["items"]:
            check("id" in i or i.get("ref") in items, f"seed: {sec['id']} has a dangling ref")
    ids.update(items)
    for src in (seed, over):
        for key in ("hours", "special_hours", "services", "diets", "allergens", "faqs",
                    "ui_components"):
            ids.update(n["id"] for n in src.get(key) or [])
    for src, key in ((seed, "unverified_diets"), (over, "verified_diets")):
        for diet, mids in src[key].items():
            for ref in [diet, *mids]:
                check(ref in ids, f"{key}: unknown id {ref}")
    components = {c["component"] for c in over["ui_components"]}
    verified = {(d, m) for d, mids in over["verified_diets"].items() for m in mids}
    names = {d["id"]: d["name"] for d in seed["diets"]}
    return ids, items, components, {(names[d], m) for d, m in verified}


def check_ids(path, raw, ids):
    for ref in sorted(set(ID_RE.findall(raw))):
        allowed = ref in ids or (ref in POST_AGENT and path.name == "gift_cards.json")
        check(allowed, f"{path.name}: id {ref} is not in seed + overlay")


def check_menu_list(name, view, items, verified):
    for it in view["data"]["items"]:
        src = items.get(it["id"])
        if not src:
            continue
        want = (src["name"], f"${src['price_cents'] / 100:,.2f}", src.get("description", ""))
        got = (it["name"], it["price"], it["description"])
        check(got == want, f"{name}: {it['id']} does not match the seed")
        for b in it["badges"]:
            ok = b["verified"] == ((b["diet"], it["id"]) in verified)
            check(ok, f"{name}: {it['id']} badge {b['diet']} has the wrong verified flag")
    ordering = any(a["name"] == "add_to_cart" for a in view["actions"])
    check(ordering == name.endswith("_order.json"), f"{name}: add_to_cart")


def check_surface(name, s, components, items, verified):
    check(set(s) == SURFACE_KEYS, f"{name}: surface keys {set(s) ^ SURFACE_KEYS}")
    check(len(s["title"]) <= 24, f"{name}: title longer than 24 chars")
    check(isinstance(s["say"], str), f"{name}: say must be a string")
    check(s["kind"] in ("answer", "gap", "off_topic", "preset"), f"{name}: bad kind")
    check(set(s["meta"]) == META_KEYS, f"{name}: meta keys")
    used = [v["component"] for v in s["views"]]
    for v in s["views"]:
        check(set(v) == VIEW_KEYS, f"{name}: view keys {set(v) ^ VIEW_KEYS}")
        check(v["component"] in components, f"{name}: unknown component {v['component']}")
        if v["component"] == "MenuList":
            check_menu_list(name, v, items, verified)
            capped = s["kind"] == "preset" or len(v["data"]["items"]) <= 12
            check(capped, f"{name}: MenuList has more than 12 items")
    if "MenuList" in used:
        check("AllergenNotice" in used, f"{name}: MenuList without AllergenNotice")
    check(used.count("GoalCTA") <= 1, f"{name}: more than one GoalCTA")
    check(not (STEER & set(used) and "GoalCTA" in used), f"{name}: GoalCTA beside a steer view")


def main():
    ids, items, components, verified = load()
    raw_intents = (DEMO / "intents.yaml").read_text()
    intents = yaml.safe_load(raw_intents)["intents"]
    texts = [i["text"] for i in intents]
    check(len(intents) == 30, f"intents: expected 30, found {len(intents)}")
    check(len(set(texts)) == len(texts), "intents: duplicate text")
    check_ids(DEMO / "intents.yaml", raw_intents, ids)

    index = json.loads((SURFACES / "index.json").read_text())
    surfaces = sorted(p for p in SURFACES.glob("*.json") if p.name != "index.json")
    found = {p.stem for p in surfaces}
    check(found == EXPECTED, f"surfaces: unexpected or missing files {found ^ EXPECTED}")
    for text, filename in index.items():
        check(text in texts, f"index.json: '{text}' is not an intent text")
        check((SURFACES / filename).is_file(), f"index.json: {filename} does not exist")
    for path in surfaces:
        raw = path.read_text()
        check_ids(path, raw, ids)
        check_surface(path.name, json.loads(raw), components, items, verified)
    readme = ROOT / "fixtures/README.md"
    if readme.exists():
        check_ids(readme, readme.read_text(), ids)

    for e in errors:
        print("FAIL", e)
    print(f"{len(items)} menu items, {len(intents)} intents, {len(surfaces)} surfaces,",
          f"{len(index)} indexed intents:", "FAILED" if errors else "OK")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
