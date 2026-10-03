"""The label and edge registries of docs/SCHEMA.md sections 5 and 6, as seed rows."""

from __future__ import annotations

from typing import NamedTuple

# Catalog entry keys (SCHEMA section 7): the public props of a UIComponent node.
UI_KEYS = [
    "component", "version", "use_when", "binds", "selectable", "preset", "cta_label",
    "rail_label", "say", "chips", "channels", "primitive", "fields", "submit_label",
]  # fmt: skip


class LabelRow(NamedTuple):
    label: str
    may_be_public: bool
    public_props: list[str]
    description: str

    @property
    def locked(self) -> bool:
        """The five non-public labels are locked: the agent can never read or write them."""
        return not self.may_be_public


class EdgeTypeRow(NamedTuple):
    type: str
    public_props: list[str]
    description: str


LABELS = [
    # Business also carries the /v1/bootstrap extras `nav` and `chips` (contract owner).
    LabelRow("Business", True,
             ["cuisine", "price_range", "phone", "url", "tagline", "timezone", "nav", "chips"],
             "The business itself: identity, contact and widget bootstrap."),
    LabelRow("Location", True,
             ["street", "city", "region", "postal", "maps_url", "parking", "transit"],
             "A physical address and how to get there."),
    LabelRow("HoursSpec", True, ["days", "opens", "closes"],
             "Regular opening hours for a set of weekdays (HH:MM; closes before opens means "
             "the next day)."),
    LabelRow("SpecialHours", True, ["date", "closed", "opens", "closes", "note"],
             "Hours on one calendar date (YYYY-MM-DD) that override the regular hours."),
    LabelRow("MenuSection", True, ["position"], "A section of the menu."),
    LabelRow("MenuItem", True, ["description", "price_cents", "currency", "available"],
             "One dish or drink on the menu."),
    LabelRow("Diet", True, ["schema_org", "synonyms"], "A diet a menu item may suit."),
    LabelRow("Allergen", True, ["fda_major", "synonyms"], "An allergen a menu item may contain."),
    LabelRow("Service", True, ["kind", "details", "min_headcount", "booking_url"],
             "Something the business offers: reservations, catering, takeout, private events."),
    LabelRow("FAQ", True, ["question", "answer"],
             "A canonical question and the owner's answer; also site content with no typed "
             "label."),
    LabelRow("UIComponent", True, list(UI_KEYS),
             "A catalog entry: one interface element the serving model may select."),
    LabelRow("Goal", False, ["statement", "priority"],
             "A private business goal; only a numeric steer weight is ever published."),
    LabelRow("KnowledgeGap", False, ["topic", "count", "sessions", "state", "origin"],
             "A topic visitors asked about that the graph could not answer."),
    LabelRow("Customer", False, ["name", "contact", "notes"],
             "A customer record. Private; never published."),
    LabelRow("ReviewSummary", True, ["rating", "count", "source", "highlights"],
             "A summary of public reviews from one source."),
    LabelRow("BrandTrait", True, ["kind", "value"], "A brand color, font or tone."),
    LabelRow("Intent", True, ["examples", "kind"], "A kind of visitor request, with examples."),
    LabelRow("Ingredient", True, [], "An ingredient of a menu item."),
    LabelRow("MediaAsset", True, ["url", "alt"], "An image or other media file."),
    LabelRow("Promotion", True, ["details", "days"], "A special offer or recurring deal."),
    LabelRow("Proposal", False, [], "Not used; replaced by change records (kg.change)."),
    LabelRow("OwnerNote", False, ["text"], "A private note from the owner."),
]  # fmt: skip

EDGE_TYPES = [
    EdgeTypeRow("HAS_LOCATION", [], "Business to Location."),
    EdgeTypeRow("HAS_HOURS", [], "Business to HoursSpec or SpecialHours."),
    EdgeTypeRow("HAS_SECTION", [], "Business to MenuSection."),
    EdgeTypeRow("HAS_ITEM", ["position"], "MenuSection to MenuItem, ordered by position."),
    EdgeTypeRow("SUITABLE_FOR", [], "MenuItem to Diet; a badge is shown only if owner-verified."),
    EdgeTypeRow("CONTAINS_ALLERGEN", [],
                "MenuItem to Allergen; shown as fact only if owner-verified."),
    EdgeTypeRow("OFFERS", [], "Business to Service."),
    EdgeTypeRow("ANSWERS", [], "FAQ to the Business, Service or MenuItem it is about."),
    EdgeTypeRow("ADVANCES", [], "UIComponent to Goal. Never published; becomes steer."),
    EdgeTypeRow("ABOUT", [], "KnowledgeGap to the FAQ or SpecialHours that answered it."),
    EdgeTypeRow("RENDERS_WITH", ["weight"], "Intent to UIComponent."),
    EdgeTypeRow("PAIRS_WITH", [], "MenuItem to MenuItem: an upsell suggestion."),
    EdgeTypeRow("CONTAINS", [], "MenuItem to Ingredient."),
    EdgeTypeRow("DEPICTS", [], "MediaAsset to any public node."),
]  # fmt: skip
