"""Keyword rules that stand in for the local model on laptops.

`select(schema, candidates, text)` returns a Selection (docs/SCHEMA.md 8.1) that is valid
against the schema it was given and names only components and ids that schema offers.
Deterministic: the same input always gives the same selection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import jsonschema

OFF_TOPIC = {"kind": "off_topic"}
TOPIC_MAX = 60


def _norm(word: str) -> str:
    """Lowercase singular form: "IPAs" -> "ipa", "sours" -> "sour", "Guinness" stays."""
    word = word.lower()
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _words(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9]+", " ", text.lower().replace("'", "").replace("’", ""))
    return cleaned.split()


def _tokens(text: str) -> list[str]:
    return [_norm(word) for word in _words(text)]


def _split_camel(label: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", label)


_STOP = set(_tokens(
    "i im id ill ive you your youre we our us me my a an the is are was were be been do does did"
    " have has had can could would will should may might what whats which who when where why"
    " how there here this that these those it its any some something anything of on in at to"
    " for with by from about and or not no yes please like want need get got show tell give"
    " much many more most also just so if then than as up out nearby near around tonight today"
    " tomorrow option kind thing one"
))
# Words too common on a menu to identify one FAQ, item or section on their own.
_GENERIC = set(_tokens("beer wine burger food drink menu item dish bar restaurant"))
_ITEM_GENERIC = set(_tokens("burger beer"))
_SECTION_GENERIC = {"beer"}
_ARTICLES = {"the", "a", "an", "and", "of", "with"}
_ALLERGY = set(_tokens("allergic allergy allergies allergen allergens"))
_BOOKING = set(_tokens("book booking reserve reservation"))
_CONTACT = set(_tokens("contact message"))
_HOURS = set(_tokens("open opened opening close closed closing hours"))
_NOT_HOURS = {"kitchen", "brunch"}
_ORDER = set(_tokens("order ordering add takeout pickup takeaway"))
_ORDER_PHRASES = (" pick up ", " take out ", " to go ", " take away ")
_CATERING_PHRASES = (" large group ", " event food ")
_CONTACT_PHRASES = (" send you a message ", " get in touch ")
_OFF_TOPIC = set(_tokens(
    "joke weather poem song story riddle president politics election code python javascript"
    " math homework translate capital bitcoin crypto stock news essay lyrics horoscope"
))
_BUSINESS = set(_tokens(
    "parking wifi menu food drink price reservation music tv game pet dog kid patio outdoor"
    " accessible wheelchair payment card cash gift delivery location address phone happy hour"
    " special event allergy vegan vegetarian gluten beer wine cocktail table seat seating"
    " dessert coffee trivia karaoke smoking dress tip bathroom restroom"
))


@dataclass
class Offer:
    """What the request's schema allows: components, and the ids each field may take."""

    components: set[str] = field(default_factory=set)
    enums: dict[str, list[str]] = field(default_factory=dict)

    def has(self, component: str) -> bool:
        return component in self.components

    def ids(self, name: str) -> list[str]:
        return self.enums.get(name, [])


def _enum_of(prop: dict) -> list[str]:
    prop = prop.get("items", prop) if prop.get("type") == "array" else prop
    values = [prop["const"]] if "const" in prop else prop.get("enum", [])
    return [value for value in values if isinstance(value, str)]


def _answer_variants(schema: dict) -> list[dict]:
    for branch in schema.get("anyOf", [schema]):
        props = branch.get("properties", {})
        if props.get("kind", {}).get("const") == "answer":
            items = props.get("views", {}).get("items", {})
            return items.get("anyOf", [items])
    return []


def parse_offer(schema: dict) -> Offer:
    offer = Offer()
    for variant in _answer_variants(schema):
        props = variant.get("properties", {})
        offer.components.update(_enum_of(props.get("component", {})))
        for name, prop in props.items():
            if name not in ("component", "order"):
                offer.enums[name] = _enum_of(prop)
    return offer


@dataclass
class Ctx:
    offer: Offer
    candidates: list[dict]
    text: str
    padded: str = ""
    tokens: set[str] = field(default_factory=set)
    content: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        words = _words(self.text)
        self.padded = f" {' '.join(words)} "
        self.tokens = {_norm(word) for word in words}
        self.content = [word for word in words if _norm(word) not in _STOP]

    def of_label(self, label: str, enum: str) -> list[dict]:
        allowed = set(self.offer.ids(enum))
        return [c for c in self.candidates if c.get("label") == label and c.get("id") in allowed]

    def has_phrase(self, phrases: tuple[str, ...]) -> bool:
        return any(phrase in self.padded for phrase in phrases)


def _answer(*views: dict) -> dict:
    return {"kind": "answer", "views": list(views)}


def _menu(ctx: Ctx, diet: str | None = None, section: str | None = None,
          items: tuple[str, ...] = ()) -> dict:
    order = bool(ctx.tokens & _ORDER) or ctx.has_phrase(_ORDER_PHRASES)
    return _answer({"component": "MenuList", "diet": diet, "section": section,
                    "items": list(items), "order": order})


def _synonym_phrases(candidate: dict) -> list[set[str]]:
    facts = candidate.get("facts", "")
    listed = facts.split("synonyms:", 1)[1].split(";", 1)[0] if "synonyms:" in facts else ""
    phrases = [set(_tokens(part)) for part in listed.split(",")]
    return [phrase for phrase in phrases if phrase]


def _diet_match(ctx: Ctx) -> str | None:
    for diet in ctx.of_label("Diet", "diet"):
        phrases = [set(_tokens(diet.get("name", ""))), *_synonym_phrases(diet)]
        if any(phrase and phrase <= ctx.tokens for phrase in phrases):
            return diet["id"]
    return None


def _allergen_score(ctx: Ctx, allergen: dict) -> int:
    ignore = _ALLERGY | {"free"}
    name = set(_tokens(allergen.get("name", ""))) - ignore
    synonyms = set().union(*_synonym_phrases(allergen), set()) - ignore
    return 2 * len(name & ctx.tokens) + len(synonyms & ctx.tokens)


def _allergen(ctx: Ctx) -> dict | None:
    allowed = ctx.offer.ids("allergen")
    if not ctx.offer.has("AllergenNotice") or not allowed:
        return None
    scored = [(_allergen_score(ctx, a), a["id"]) for a in ctx.of_label("Allergen", "allergen")]
    best = max(scored, key=lambda pair: pair[0], default=(0, allowed[0]))
    named_free = "free" in ctx.tokens and ("nut" in ctx.tokens or best[0] > 0)
    is_diet = "gluten" in ctx.tokens or _diet_match(ctx) is not None
    if not ctx.tokens & _ALLERGY and not (named_free and not is_diet):
        return None
    chosen = best[1] if best[0] > 0 else allowed[0]
    return _answer({"component": "AllergenNotice", "allergen": chosen})


def _catering(ctx: Ctx) -> dict | None:
    wanted = any(t.startswith("cater") for t in ctx.tokens) or ctx.has_phrase(_CATERING_PHRASES)
    if wanted and ctx.offer.has("CateringQuoteForm"):
        return _answer({"component": "CateringQuoteForm"})
    return None


def _booking(ctx: Ctx) -> dict | None:
    wanted = bool(ctx.tokens & _BOOKING) or " table for " in ctx.padded
    if wanted and ctx.offer.has("BookingForm"):
        return _answer({"component": "BookingForm"})
    return None


def _form_words(form_id: str) -> set[str]:
    return set(_tokens(form_id)) - {"ui", "form", "request"}


def _matching_label(ctx: Ctx) -> str | None:
    if not ctx.offer.has("ListCard"):
        return None
    for label in ctx.offer.ids("label"):
        if set(_tokens(_split_camel(label))) <= ctx.tokens:
            return label
    return None


def _form(ctx: Ctx) -> dict | None:
    if not ctx.offer.has("FormCard"):
        return None
    forms = ctx.offer.ids("form")
    if ctx.tokens & _CONTACT or ctx.has_phrase(_CONTACT_PHRASES):
        for form in forms:
            if _form_words(form) & _CONTACT:
                return _answer({"component": "FormCard", "form": form})
    for form in forms:
        words = _form_words(form)
        if words and words <= ctx.tokens:
            card = {"component": "FormCard", "form": form}
            label = _matching_label(ctx)
            if label:
                return _answer({"component": "ListCard", "label": label}, card)
            return _answer(card)
    return None


def _hours(ctx: Ctx) -> dict | None:
    if ctx.tokens & _HOURS and not ctx.tokens & _NOT_HOURS and ctx.offer.has("HoursCard"):
        return _answer({"component": "HoursCard"})
    return None


def _best_faq(ctx: Ctx) -> tuple[int, str | None]:
    """(shared content words, faq id) for the FAQ sharing the most, needing one specific word."""
    asked = {_norm(word) for word in ctx.content}
    best: tuple[int, str | None] = (0, None)
    for faq in ctx.of_label("FAQ", "faq"):
        words = set(_tokens(f"{faq.get('name', '')} {faq.get('facts', '')}")) - _STOP
        shared = asked & words
        if shared - _GENERIC and len(shared) > best[0]:
            best = (len(shared), faq["id"])
    return best


def _faq(ctx: Ctx, minimum: int) -> dict | None:
    if not ctx.offer.has("Answer"):
        return None
    shared, faq_id = _best_faq(ctx)
    if faq_id is None or shared < minimum:
        return None
    return _answer({"component": "Answer", "faq": faq_id})


def _faq_strong(ctx: Ctx) -> dict | None:
    return _faq(ctx, 2)


def _faq_weak(ctx: Ctx) -> dict | None:
    return _faq(ctx, 1)


def _item_score(ctx: Ctx, item: dict) -> int:
    """How many identifying name words the text has; 0 unless the item is clearly named."""
    words = set(_tokens(item.get("name", ""))) - _ARTICLES
    generic = words & _ITEM_GENERIC
    specific = words - generic
    if not specific or not specific <= ctx.tokens:
        return 0
    if len(specific) < 2 and generic and not generic <= ctx.tokens:
        return 0
    return len(specific)


def _named_items(ctx: Ctx) -> dict | None:
    if not ctx.offer.has("MenuList"):
        return None
    scored = [(_item_score(ctx, item), item["id"]) for item in ctx.of_label("MenuItem", "items")]
    top = max((score for score, _ in scored), default=0)
    if top == 0:
        return None
    return _menu(ctx, items=tuple(item for score, item in scored if score == top)[:6])


def _section_parts(name: str) -> list[set[str]]:
    """A section name split at "&", "," and "and": "Porters & Stouts" is two ways to ask."""
    parts = [set(_tokens(part)) - _STOP for part in re.split(r"&|,|\band\b", name)]
    return [part for part in parts if part]


def _section_match(ctx: Ctx, strict: bool) -> str | None:
    """Strict: every identifying word of a part is in the text. Loose: any word is."""
    best: tuple[int, str | None] = (0, None)
    for section in ctx.of_label("MenuSection", "section"):
        for part in _section_parts(section.get("name", "")):
            specific = part - _SECTION_GENERIC or part
            hit = specific <= ctx.tokens if strict else bool(part & ctx.tokens)
            if hit and len(part) > best[0]:
                best = (len(part), section["id"])
    return best[1]


def _diet(ctx: Ctx) -> dict | None:
    diet = _diet_match(ctx) if ctx.offer.has("MenuList") else None
    if diet is None:
        return None
    return _menu(ctx, diet=diet, section=_section_match(ctx, strict=True))


def _section(ctx: Ctx) -> dict | None:
    if not ctx.offer.has("MenuList"):
        return None
    section = _section_match(ctx, strict=True) or _section_match(ctx, strict=False)
    return _menu(ctx, section=section) if section else None


def _generic_cards(ctx: Ctx) -> dict | None:
    allowed = set(ctx.offer.ids("node")) if ctx.offer.has("FactCard") else set()
    for node in ctx.candidates:
        words = set(_tokens(node.get("name", ""))) - _ARTICLES
        if node.get("id") in allowed and words and words <= ctx.tokens:
            return _answer({"component": "FactCard", "node": node["id"]})
    label = _matching_label(ctx)
    return _answer({"component": "ListCard", "label": label}) if label else None


def _fallback(ctx: Ctx) -> dict:
    asked = {_norm(word) for word in ctx.content}
    if not asked or asked & _OFF_TOPIC:
        return dict(OFF_TOPIC)
    if not ctx.candidates and not asked & _BUSINESS:
        return dict(OFF_TOPIC)
    topic = " ".join(ctx.content)[:TOPIC_MAX].strip()
    return {"kind": "gap", "topic": topic}


# Order matters: forms and hours first, then a well-matched FAQ, a named item, an explicit
# diet, a loosely matched FAQ, a section, and last the generic cards.
_RULES = (_allergen, _catering, _booking, _form, _hours, _faq_strong, _named_items, _diet,
          _faq_weak, _section, _generic_cards)


def _decide(ctx: Ctx) -> dict:
    for rule in _RULES:
        pick = rule(ctx)
        if pick is not None:
            return pick
    return _fallback(ctx)


def is_valid(schema: dict, selection: dict) -> bool:
    try:
        jsonschema.validate(selection, schema)
    except jsonschema.ValidationError:
        return False
    return True


def select(schema: dict, candidates: list[dict], text: str) -> dict:
    """The Selection for one request; `{"kind": "off_topic"}` if the pick does not validate."""
    pick = _decide(Ctx(parse_offer(schema), candidates, text))
    return pick if is_valid(schema, pick) else dict(OFF_TOPIC)
