# CAC — Product Requirements Document

| | |
|---|---|
| Working title | CAC: Chats, Agents, Context |
| Event | Dell x NVIDIA AI Hackathon, Boston, Saturday 3 October 2026 |
| Challenge | "Ship an always-on AI agent running fully local on the Dell Pro Max with GB10" |
| Status | Version 3, 3 October 2026. Version 2 followed four independent reviews. Version 3 makes the self-evolving graph a core capability: the agent can add node types, edge types and props, tag and edit existing data, and add new elements |
| Companion | [SCHEMA.md](SCHEMA.md): runtime, database, catalog, and wire contracts for scaffolding |
| Research | [research/](research/README.md): the six fact-checked research reports behind this document |

> **Deadline.** The event page's timestamps are 14:00 UTC on 3 October to 02:00 UTC on
> 4 October, which is 10:00 AM to 10:00 PM Eastern. A second listing says 9:00 AM to 9:00 PM,
> the schedule the other cities used. No listing shows 2 PM to 2 AM local. **Work to a 9:00 PM
> Eastern submission deadline until an organizer says otherwise.**

## 1. Summary

CAC is a local agent that a small business owns. It turns the business's existing website into
a knowledge graph, then serves that knowledge two ways from one box:

1. **To people on the website.** A visitor types what they want. The agent answers with
   owner-approved interface elements (a filtered menu, a booking form, a catering quote form)
   instead of chat text. Clicks follow fixed paths with no model call.
2. **To AI assistants acting for customers.** Claude or ChatGPT asks the restaurant's agent
   and gets the same governed answer, including an interactive element.

Behind both, an always-on agent evolves the graph from what customers ask. It answers gaps by
asking the owner, and it changes the graph itself: it adds new node types, relationship
types and properties, tags and edits existing data, and adds new interface elements. It writes
freely to the private graph; what reaches the public side passes an approval tier the owner
sets. Private data cannot cross to the public side, because the serving process has no
database permission to read it.

The name: WIMP (windows, icons, menus, pointers) made the business guess what visitors want.
CAC (chats, agents, context) lets the visitor say it. It is also aimed at the other CAC,
customer acquisition cost: every answer leans toward an owner goal such as a booking or a
catering lead. We have no conversion data yet.

### Changes from the whiteboard, and why

| Whiteboard plan | What we found | Decision |
|---|---|---|
| Claude visits the site and is redirected to an A2A endpoint | No consumer assistant speaks A2A to arbitrary sites. Claude's web fetch cannot call URLs it composes and cannot POST. Claude and ChatGPT do render MCP Apps from a connected MCP server | Flow 2 is an MCP server with an MCP Apps element, added to Claude as a custom connector. An A2A agent card is a later adapter |
| The local LLM builds the UI | Google's paper reports 29–60% output errors for its older small models on one prompt set and generation times of a minute or more. Constrained decoding guarantees valid JSON, not a correct choice | The model chooses an element and ids from a list under a JSON-schema constraint. Code writes every word and number |
| Every request goes through the NemoClaw agent | NVIDIA's tutorial quotes 30–90 s per agent response with the 120B model, and NemoClaw's gateway is built for one trusted operator, not anonymous visitors | Visitors get one constrained completion from the same local model. The NemoClaw agent does the always-on work. This is also a security decision: anonymous text never drives an agent that holds tools |
| Three sub-agents: graph, visitor-facing, assistant-facing | An agent loop per request is too slow, and NemoClaw does not host public listeners | One NemoClaw agent for the graph and the owner. The visitor-facing and assistant-facing roles are plain services using the same local model. Splitting the agent in two (Gardener, Liaison) is P1 |
| The LLM creates new elements; the owner approves | An element is a prebuilt React component, so a brand-new one needs code | Kept, in P0. Three generic components (`FormCard`, `FactCard`, `ListCard`) let the agent add elements and show new node types as configuration, with no new code |
| A self-evolving graph agent | Structure can live in data: labels and edge types are rows, props are JSON | Kept, in P0. The agent changes structure and content through recorded, reversible change records; publishing is gated by an approval tier |
| Elements are A2UI | Shipping an A2UI renderer in the widget and the MCP App is work with no demo payoff | Our own catalog JSON using A2UI's vocabulary (catalog, surface, action) |
| The local LLM classifies dishes itself | A wrong diet or allergen tag is a safety problem | Kept. The agent tags dishes itself and the tag goes live marked "not verified, ask staff". The verified badge appears only after the owner taps confirm |
| "Only desserts" refinement, cart checkout, microphone | Time | Refinement and cart checkout are P1. Voice is P2. The know-versus-order distinction stays in P0 |

## 2. Glossary

| Term | Meaning |
|---|---|
| Element, component | A prebuilt, owner-approved piece of interface (menu list, booking form). The whiteboard said "element"; the schema says "component". Same thing |
| Catalog | The owner-approved set of components the model may choose from |
| Surface | One response: a sentence plus up to two chosen components and up to two inserted by code |
| Selection | The model's output: a component name and ids from a list it was given |
| Binder | Code that checks a selection and fills it with graph data |
| Preset | A fixed surface for a nav button or call to action, served with no model call |
| Slot | A value code pulls from typed text before the model runs: date, time, party size |
| Publish | The step that copies approved public data to the store the serving side can read |
| Steer | A per-component weight derived from the owner's private goals |
| Gap | A question the graph could not answer |
| Change record | One recorded, reversible write by the agent: a new node type, a tag, an edit, a new element |
| Approval tier | Whether a change publishes automatically, waits for one owner tap, or is refused. Set by the owner's autonomy setting (cautious, balanced, free) |
| Generic component | `FactCard`, `ListCard`, `FormCard`: components driven by configuration, so new node types and elements need no new code |
| Canary | A fake private record with a unique name, used to prove nothing private leaks |
| OpenClaw | The always-on agent framework the challenge requires |
| OpenShell | The sandbox OpenClaw agents run in; it enforces a network allowlist |
| NemoClaw | NVIDIA's package that installs OpenClaw inside OpenShell with a managed local model server |
| Heartbeat | The timer that wakes an always-on agent |
| MCP, connector | The protocol Claude and ChatGPT use to call external tools. A connector is an MCP server a user has added |
| MCP Apps | The MCP extension that lets a tool return an interactive component, rendered by Claude and ChatGPT |
| A2UI | Google's open spec for agent-requested UI from a client-side catalog (v0.9.1; v1.0 candidate) |
| A2A | Agent-to-agent protocol (1.0). Used between enterprise agents, not by consumer assistants today |
| Tunnel | An outbound connection that gives the box's MCP server a public HTTPS address |

## 3. Hackathon constraints

| Fact | Source and confidence |
|---|---|
| Runs Saturday 3 October, most likely 10 AM to 9 or 10 PM Eastern (see the deadline note above) | Event page timestamps; series pages |
| Agent must run fully local on the Dell Pro Max with GB10; first prize is the box | Event page |
| Required stack is OpenClaw + NVIDIA NemoClaw + OpenShell; "an AI agent that runs locally on the box (no cloud API)"; demo on the provided box; submit through BuilderBase; top 8 pitch live | Pages for other cities in the series. Not stated on the Boston page |
| Judging 25% pitch, 25% local, 25% business value, 25% technical | The team's understanding. Not published anywhere we could find |
| "A real business or corporate workflow, not a toy demo" | Cornell page for the same series |
| Venue Wi-Fi is not enough for model downloads | NYC page for the same series |

Hardware: GB10 Grace Blackwell, 128 GB unified memory, DGX OS 7. NemoClaw is alpha software
(v0.0.130 on 1 October 2026), installs by script, and does not restart on its own after a
reboot.

## 4. Problem

**For the owner.** A restaurant's knowledge lives in a site built for browsing: a PDF menu,
an hours table, a contact form. The owner pays platforms to reach customers: Owner.com is
$249/month plus 5% per order or $499/month flat, with a further 5% fee charged to guests on
both plans; DoorDash takes 15–30% on delivery.

**For the visitor.** The site makes them hunt. "Which dishes are vegetarian?", "are you open
on the 4th?", and "do you cater for 40?" each mean scanning pages or calling.

**For AI assistants.** 45% of US consumers used generative AI for local business
recommendations in 2026, up from 6% in 2025 (BrightLocal, n=1,002). Assistants read sites
badly: in a December 2024 Vercel/MERJ study, OpenAI's, Anthropic's and Perplexity's crawlers
fetched JavaScript but did not run it, and Claude's web fetch does not render JavaScript. A
developer's August 2026 test of 200 Amsterdam restaurants (published by the author of a
booking MCP server) found 16 could be taken to the final booking step by a browser agent, and
none of 163 working sites exposed an interface an assistant could call.

**The gap in current answers.** Square, Toast, OpenTable, Resy and Yelp already put
restaurants inside ChatGPT, Claude and Google Maps. In each case the restaurant is a row in
the platform's catalog, and the platform or the assistant decides what is shown. On the
booking aggregators the platform also owns ranking and the guest. We found nobody giving the
owner their own agent, on their own hardware, answering both people and assistants from one
governed source.

## 5. Product principles

1. **The owner owns the agent.** The box, the graph, the goals, and the approved interface
   belong to the business.
2. **One graph, two audiences.** People and assistants get the same facts from the same place.
3. **Typed intent goes to the model; clicks do not.** Buttons, forms, and navigation are fixed
   paths. Suggested chips submit their text as an intent and are pre-warmed in the cache.
4. **The model chooses, code writes.** The model picks a component and ids. Every word, price,
   hour, and badge a visitor sees comes from the graph or a template.
5. **Private by structure.** The serving process cannot read private data. This is a database
   permission, not a prompt instruction.
6. **Anonymous text never drives an agent that holds tools.** Visitors get a tool-less
   completion. The agent sees clustered topics and counts, never raw visitor text.
7. **The agent writes freely; publishing is gated.** The agent may change anything in the
   private graph, including its structure. Every change is recorded and reversible. The
   owner's autonomy setting decides what publishes on its own and what waits for a tap. Only
   the owner can mark something verified.
8. **Every answer leans toward an owner goal**, and never at the cost of answering the
   question.
9. **Keep the existing site.** CAC is an added panel. If the box is unreachable, the site
   behaves exactly as before.

## 6. Users

| User | Wants | CAC gives them |
|---|---|---|
| Owner | More bookings and catering leads, less platform dependence, no new dashboard to learn | An agent that reads their site, asks them only what it cannot find, and steers toward their goals |
| Site visitor | A fast answer and the next step | An intent box that returns the right element, with the nav bar still there |
| Customer's AI assistant | Facts it can trust and an action it can take | Tools that return owner-confirmed data and a booking request |

## 7. Scope

**P0: must work in the demo**

- One fictional demo restaurant. A single seed file drives both the graph and the static demo
  site.
- Graph with public/private partition, publish step, and allowlisted props.
- Flow 1: website panel with intent box; components `Answer`, `MenuList`, `HoursCard`,
  `BookingForm`, `CateringQuoteForm`, plus `AllergenNotice` and `GoalCTA` inserted by code;
  presets for nav; forms that store leads; "Add" buttons with a cart count when the visitor
  wants to order; exact cache; cache pre-warm after each publish.
- Flow 3: one NemoClaw agent that evolves the graph. It puts unanswered questions to the
  owner and publishes the reply, and it makes its own changes: new node types, edge types
  and props; tags and edits on existing data; new elements.
- Generic components `FactCard`, `ListCard` and `FormCard`, so what the agent adds can be
  shown with no new code.
- Change records with approval tiers, and an owner inbox page: pending changes with approve
  and reject, unverified tags with confirm, applied changes with revert, new leads.
- Privacy proof: permission-denied queries shown live, canary script, blocked egress.
- Live overlay: latency, cache hits, model calls in flight, model host, leads captured.

**P1: only after the P0 gates pass**

- Flow 2: MCP server with the MCP Apps element in Claude.
- Ingesting the demo site's JSON-LD (instead of the seed) as the onboarding proof.
- Refinement ("only desserts"). Cart review and pickup order as a lead. `LocationCard`,
  `ItemCard`, `ReviewHighlights`. History rail. Slot-masked and semantic cache.
- Agent split into Gardener and Liaison. Owner-initiated facts. Onboarding interview. More
  triggers for the agent (goal buttons nobody clicks, site re-crawl differences).

The self-evolving loop is P0 and comes before Flow 2. With a 9 PM deadline, expect Flow 2 to
be shown as a recording or left as roadmap.

**P2: say as roadmap**

- LLM extraction from page text, PDF and image menus. A2A agent card. Voice. WebMCP tools.
  UCP profile once the food vertical ships. Multi-box clustering.

**Non-goals**

- Payments. Rebuilding the owner's site. An owner dashboard beyond the inbox page.
  Multi-tenant hosting in v0. Any cloud model call from the business side. Confirmed
  reservations (we create requests).

## 8. Experience

### Flow 0: Onboarding

1. The owner gives the site URL.
2. Ingestion parses structured data (schema.org JSON-LD) in code. Typed fields parsed by code
   (names, prices, hours, address) are approved in bulk when the owner says "publish".
3. Anything a model read from page text, a PDF, or an image stays a draft until the owner
   approves it. Diet and allergen tags stay unverified until the owner confirms them.
4. A completeness check lists what is missing (holiday hours, parking, catering minimum, diet
   tags). Each becomes a gap the agent asks the owner about.
5. The owner states goals ("more weeknight bookings", "sign up catering clients"). They become
   private Goal nodes.
6. Publish. The owner adds one script tag to the site.

In the hackathon build, steps 1 to 5 are replaced by loading the seed file; JSON-LD ingest is
P1 and the rest is roadmap.

Acceptance (P0): one command loads the seed and publishes a graph with at least 20 menu items,
hours, two special-hours dates, two services, and two private goals that appear on the public
side only as `steer` weights on two components.

### Flow 1: Visitor on the website

Layout (from the wireframe): the existing header and nav stay. The panel has the current
surface in the centre and the intent box with suggested chips at the bottom. A history rail on
the left (earlier answers as chips, kept in the browser) is P1. Each typed intent is
independent in P0.

| Visitor does | Result | Model call |
|---|---|---|
| Types "vegetarian options" | Menu list titled "Vegetarian". Owner-confirmed dishes carry a badge; unconfirmed ones say "not verified, ask staff". No "Add" buttons (they want to know, not order). Allergy notice. "Book a table" button | once; cached after |
| Types "I want to pick up something vegetarian" | The same list with "Add" buttons; adding updates a cart count | once |
| Types "are you open on the 4th of July?" | Hours card with the answer computed from hours data ("Closed on Sunday 4 July 2027"), plus a "Book a table" button | once, to route; the answer is code |
| Types "do you cater for 40?" | Catering quote form with 40 filled in. No booking button, because this surface already serves a goal | once |
| Types "do you have gluten-free pasta?" (nothing confirmed) | "We haven't confirmed that yet. Please ask our staff." with the phone link. Logged as a gap | once |
| Types "I'm allergic to peanuts" | A fixed caution and only the dishes confirmed to contain peanuts. Never a list of "safe" dishes | once |
| Types "do you sell gift cards?" after the agent added that type and form | A list of gift card options and a request form, both from generic components | once |
| Types something off topic | "I can help with our menu, hours, bookings and catering." | once |
| Clicks nav "Menu", a chip's preset, "Book a table", "Add" | Preset surface or cart count | none |
| Submits a form | Lead stored; confirmation shown | none |
| Asks something already asked | Instant answer | none (cache) |

Acceptance:

- Uncached typed intent returns in under 2.5 s at median with one request in flight on the
  box; cached in under 200 ms; clicks in under 100 ms. Replace these targets with measured
  numbers after the first-hour benchmark.
  Measured on the box at 14:45 (nico's selection benchmark, `qwen3.6:35b` on Ollama, one
  constrained completion per intent): median 0.25 s and p95 0.30 s with one request in
  flight; median 0.96 s and p95 1.06 s with four, because Ollama serves one request at a
  time. Measured on a laptop: retrieval, binding and logging add 6 to 30 ms; a cache hit
  or a preset returns in under 10 ms.
- 30 fixture intents: 100% schema-valid, at least 27 routed to the right component.
- An unverified diet claim is never shown as fact. An allergen question never yields a list of
  safe dishes.
- The same question asked twice produces one model call.
- If the model times out or the queue is full, the visitor gets the menu preset with a "we're
  busy" note. No cloud model is ever called.

### Flow 2: A customer's assistant (P1)

1. The customer has added the restaurant's connector in Claude and switched it on in the chat.
   They ask: "Ask <restaurant name> whether it works for dinner tonight. One of us is
   vegetarian, one loves meat."
2. Claude calls `ask_restaurant`. The MCP server on the box runs the same pipeline over the
   public graph.
3. Claude receives text built from graph facts and renders the restaurant's own element
   inline.
4. The customer taps "Request a table". The element calls `request_booking`. The lead appears
   in the owner inbox on the box.

What is true today, to say plainly: the customer adds the connector by URL once (Claude:
Customize > Connectors, one custom connector on the Free plan; ChatGPT: Developer mode). That
is more steps than a directory app. No assistant discovers a business's agent from its URL on
its own. MCP and MCP Apps are the standards; the graph, the partition, and the selection are
ours.

Acceptance: from Claude, the question returns a rendered element with correct data; a booking
request creates a lead; asking for customer names returns nothing private. Tested with Claude's
web search both on and off, with "Always allow" already clicked.

### Flow 3: The always-on loop

The agent wakes on a heartbeat, reads what visitors have been asking (clustered topics and
counts, never raw text), reads the current graph and its structure, and decides what to
change. It has two kinds of move.

**Ask the owner** (when only the owner knows the answer)

1. "5 visitors asked about gluten-free pasta. I have nothing confirmed. What should I tell
   them?"
2. The owner replies in plain words. The agent turns the reply into the right typed update:
   an FAQ in the owner's exact words, or a special-hours entry ("we're closed on the 24th").
3. It publishes. The next visitor gets the answer, marked "Confirmed by the restaurant".

**Change the graph itself** (when the graph's content or shape is what is missing)

| The agent notices | It does | What the visitor sees next |
|---|---|---|
| 12 people asked about gift cards; no node type holds that | Creates a `GiftCard` node type with `amounts` and `terms`, adds nodes, and adds a gift-card request form built on `FormCard` | A list of gift card options and a request form |
| People ask "what's spicy?"; dishes have no such property | Adds a `spice_level` prop to MenuItem and fills it in from the descriptions | Spice level on dishes |
| The risotto has no meat or fish in its description | Tags it `SUITABLE_FOR` Vegetarian | The dish appears under Vegetarian, marked "not verified, ask staff", until the owner taps confirm |
| A dish description on the site changed | Edits the node | The new description, once approved |
| Two dishes are often asked about together | Adds a `PAIRS_WITH` link, or creates a new relationship type if none fits | "Goes well with" suggestions |

Every one of these is a change record with the agent's reason and its evidence. What happens
next depends on the owner's autonomy setting:

| Setting | Behaviour |
|---|---|
| Cautious | Everything public waits for one owner tap |
| Balanced (default, used in the demo) | Tags and links that render with their own "not verified" marker publish at once. New node types, new public props, new elements, new facts, and edits to existing facts wait for one tap |
| Free | Everything publishes at once. The owner reviews in the digest and can revert any change |

In every setting, three things stay with the owner: marking anything verified, anything
touching customers, leads or goals, and making a private type public.

The owner's inbox page shows pending changes with approve and reject, unverified tags with
confirm, applied changes with revert, and new leads. The agent cannot approve its own
changes: approval uses a credential it does not have.

The same heartbeat sends the owner a digest: questions today, top topics, changes made and
pending, new leads by kind. Lead details stay in the inbox on the box.

Heartbeat: OpenClaw's default is 30 minutes. Set it to 5 minutes, and for the demo send the
agent a "check now" message.

Acceptance:

- An unanswered question is answered correctly for the next visitor after one owner reply,
  with no code change and no restart.
- From a cluster of questions about something the graph has no type for, the agent creates a
  node type, nodes, and a form element. After one owner tap, a visitor asking about it gets a
  list and a form, with no code change and no restart.
- The agent tags a dish; it appears marked "not verified"; after the owner confirms, it shows
  the badge.
- An edit the owner reverts is gone on the next request.
- The agent's attempts to mark something verified, read a customer, or approve a change are
  refused.
- Measure one agent turn in the first 30 minutes and write the number here.

## 9. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| G1 | Load seed data into typed nodes and edges with source and verification status | P0 |
| G2 | Label and edge-type registries mark what may be published. They are data: rows can be added at run time with no migration | P0 |
| G3 | `publish()` copies approved public nodes with allowlisted props, bumps the graph version, clears stale cache | P0 |
| G4 | Retrieval is vector entry plus fixed expansion; the model never writes a query | P0 |
| G5 | Diet badges only for owner-verified edges; allergen questions never produce a safe list | P0 |
| G6 | Ingest JSON-LD from the demo site; caps on name and description length; URLs and control characters stripped | P1 |
| S1 | `POST /v1/intent` returns a surface built from approved components | P0 |
| S2 | Model output constrained to approved components and retrieved ids; the model writes no visitor-facing text | P0 |
| S3 | Presets and actions never call the model | P0 |
| S4 | Exact cache keyed on a hash of the normalized text, slots, and graph version | P0 |
| S5 | Publish replays top and demo intents to pre-warm the cache | P0 |
| S6 | Code inserts the allergy notice and at most one goal button | P0 |
| S7 | Input limits, off-topic and gap surfaces, model timeout and in-flight cap with a preset fallback. No cloud client exists in the code | P0 |
| S8 | Semantic cache; slot-masked cache; refinement | P1 |
| W1 | One script tag adds the panel in a sandboxed iframe; a health check makes it a no-op if the box is down | P0 |
| W2 | Five purpose-built components, three generic ones (`FactCard`, `ListCard`, `FormCard`), plus `AllergenNotice` and `GoalCTA` render from surface JSON | P0 |
| W3 | Suggested chips from the catalog's fixed lists, never from visitor logs | P0 |
| W4 | Existing nav links open presets | P0 |
| W5 | History rail; theme from brand traits | P1 |
| A1 | One NemoClaw agent on a heartbeat: read topics and the graph, ask the owner about gaps, record the reply as an FAQ or special hours, publish | P0 |
| A2 | The agent can create node types, edge types and props; create, edit, tag and retire nodes and edges of any unlocked type; and create elements on the generic components. Each write is a change record with a reason and evidence | P0 |
| A2a | Approval tiers by autonomy setting (cautious, balanced, free); owner-only approve, reject, revert and verify; the agent cannot read visitor text, lead details or locked types, and cannot mark anything verified | P0 |
| A2b | New node types and elements are selectable on the first request after publish, with no restart | P0 |
| A3 | The agent runs in the OpenShell sandbox with default-deny egress; the policy allows only the Owner tools API, the model endpoint, and the owner channel | P0 |
| A4 | Heartbeat digest to the owner | P0 |
| A5 | Owner-initiated facts, onboarding interview, more agent triggers | P1 |
| X1 | MCP server: profile, ask, view, booking request, catering quote | P1 |
| X2 | `ask_restaurant` returns the widget bundle as an MCP Apps element | P1 |
| X3 | A2A agent card | P2 |
| O1 | Metrics endpoint and overlay: latency, cache hits, in flight, model host, leads captured, goal buttons shown and clicked | P0 |
| O2 | Permission-denied check and canary script against every public endpoint | P0 |
| O3 | Load test at 1, 4, and 8 concurrent intents, once with an agent turn in flight | P0 |
| O4 | Owner inbox page: pending changes (approve, reject), unverified tags (confirm), applied changes (revert), new leads, open gaps | P0 |

## 10. Privacy and safety

**Invariants**

1. The serving role has no grant on the private schema. A prompt injection that fully controls
   the model still cannot read a customer record: the process holding the model's output has
   no path to that data.
2. Publish copies only allowlisted props of approved public nodes. A private prop on a public
   node is dropped.
3. The model can only name ids that were retrieved from the public store for that request, and
   it writes no text a visitor sees.
4. Goals are private. The serving side sees a number per component, not the goal.
5. Raw visitor text and leads go to tables the serving role can insert into but not read. The
   cache holds a hash of the question, not the question.
6. The agent can change the private graph freely, including its structure, but everything it
   writes is unverified by construction, recorded, and reversible. It never sees raw visitor
   text, lead details, or locked types (goals, gaps, customers). It cannot mark anything
   verified, approve its own changes, or make a private type public. The one exception is
   the owner's own words relayed from the owner's identity on the owner channel.
7. Card numbers, SSNs, and licence numbers are never stored anywhere in CAC.

Of the four options on the whiteboard we use three together: a separate store (schema plus
role), node classification (label registry with a prop allowlist), and owner approval at
publish. "Elements limit data flow" is each component's `binds` field.

**Why not rely on the sandbox for this.** NemoClaw sub-agents share one sandbox and its docs
say file permissions do not isolate them; NVIDIA also notes no sandbox fully stops prompt
injection. The sandbox limits where the agent can connect. The database role limits what the
public side can read. The tool list limits what the agent can write. The demo shows all three.

**Residual risk.** Giving the agent this much room makes it a larger target. The only path
from a visitor to the agent is a topic phrase of at most 60 characters, so a crafted question
could at worst lead the agent to propose a misleading node or tag. In balanced mode new facts
and types wait for the owner's tap, and a tag shows as "not verified". In free mode a bad
change can go live until the owner reverts it, which is why free is not the default. Nothing
the agent does can expose private data, because the serving side reads only what publish
copied from unlocked, public types.

**What leaves the box.** Nothing from Flow 1 or Flow 3 when the owner channel is the local
OpenClaw dashboard, so both run with the network unplugged. If the owner chooses a messaging
app, the aggregated question and their reply pass through it. In Flow 2, whatever a customer
sends through their own assistant passes through that assistant's cloud and the tunnel.

**Food safety.** The FDA lists nine major allergens and sets no safe threshold. schema.org's
`MenuItem` has no allergen property, only `suitableForDiet` with 11 diet values and none for
nut-free or dairy-free. So diet and allergen edges carry `verified_by_owner`, unverified
claims render as "not verified, ask staff", and an allergen question returns a fixed caution
with only the dishes confirmed to contain it. Massachusetts requires printed menus and menu
boards to carry the notice "Before placing your order, please inform your server if a person
in your party has a food allergy" (105 CMR 590.011(C)(2)); `AllergenNotice` uses the same
wording. Whether the rule reaches a web panel was not determined.

**Proof in the demo**

- As the serving role: `select * from kg.node` returns "permission denied for schema kg";
  `select * from ops.lead` returns "permission denied for table lead". This was verified in a
  test database with the DDL in SCHEMA.md.
- The canary script: a fake customer with a unique name sits in a Customer node, a lead, and
  the intent log. The script sends 40 prompts to every public endpoint and fails if the name
  appears anywhere.
- The agent tries to reach a host outside the OpenShell policy and is blocked on screen. The
  policy file is shown: Owner tools API, model endpoint, owner channel.

## 11. Architecture

```
  Visitor's browser                         Customer's assistant (Claude, ChatGPT)
  existing site + script tag                custom connector: MCP + MCP Apps
          |                                              |
==========|================ LAN / tunnel ================|=========================
          v                                              v
   Widget (React, iframe) ---> Serve API <------- MCP server (public tools, P1)
                                 |    |
                  role cac_serve |    +---> Local model server (vLLM), JSON-constrained
                                 v
        Postgres + pgvector:  kg_public  <--- publish() ---  kg (full graph)  +  ops
                                                                   ^
                                                    role cac_owner |
   NemoClaw + OpenShell sandbox                                    |
   OpenClaw agent  ---------------------->  Owner tools API -------+
          |                                 (host only, token, not tunnelled)
          +--- local dashboard (or a messaging app) ---> Owner

  Everything below the double line runs on the Dell Pro Max with GB10.
```

Processes, ports, and environment variables are in SCHEMA.md section 2.

**Where NemoClaw is load-bearing.** The challenge is an always-on agent, and the series
requires this stack. In CAC the agent is what makes the product learn: without it the graph is
a static export. It does work a script cannot: it reads what visitors want and what the graph
holds, decides whether the missing piece is a fact, a tag, a property, a new node type, a new
relationship or a new element, and makes that change. It also reads the owner's free-text
reply and decides which typed update it is.
OpenShell is what lets us give that agent write tools safely: its policy allows three
destinations and nothing else. Visitors do not go through the agent loop, by design (principle
6) and for speed.

**Plan B if organizers require every model call to pass through the agent.** Keep presets and
cache hits direct. Send each cache miss as a message to an OpenClaw agent whose single tool is
the selection function, accept the measured latency, and pre-warm the demo intents.

**Model.** One model for everything: the 30–35B model already on the box behind NemoClaw's
managed vLLM (the Spark default is `nvidia/Qwen3.6-35B-A3B-NVFP4`; a Nemotron 3.5 Lightning
30B profile exists and is marked experimental). Do not download at the venue and do not load a
second large model beside it. Thinking is disabled per request on the visitor path.

**Embeddings.** Not confirmed on the box. Decide in the first 30 minutes, in this order:
`bge-m3` or `qwen3-embedding:0.6b` if already present; any embedding model on disk; otherwise
Postgres full-text search plus trigram matching behind the same retrieve function.

**Capacity.** Output tokens are the latency budget, so the selection is tiny (about 20–40
tokens). Two blog benchmarks of this model class on the GB10 bracket single-stream decode at
21 tokens/s (FP8) and 97 tokens/s (NVFP4; the higher figure is optimistic). At 8 concurrent,
per-stream speed falls to about 42 tokens/s (NVFP4) or 10 (FP8). NemoClaw's managed vLLM
defaults to 4 concurrent sequences; decide whether to raise it in the first 30 minutes, since
changing it needs a model reload. Our estimate, to be replaced by the first-hour measurement:
1–2 uncached intents per second. Clicks and cache hits make no model call.

**Hosting.** There is no cloud deployment. The only external piece is the tunnel that lets
assistants reach the MCP server in Flow 2.

## 12. Data and schema

Full definitions are in [SCHEMA.md](SCHEMA.md). In short:

- Typed nodes and edges in Postgres, each with visibility, status, source, and owner
  verification.
- Public: business, location, hours, menu sections and items, diets, allergens, services,
  FAQs, UI components.
- Never public: goals, knowledge gaps, customers, leads, the raw intent log.
- "Vegetarian" is a node, not a column. Items connect to it. Asking for vegetarian finds the
  node by vector search and follows its edges, which is the design from the whiteboard.
- UI components are nodes too, connected to the goals they advance.
- The structure is data: node types and edge types are rows, props are JSON. The agent adds
  to them through change records, and the generic components show whatever it adds.

## 13. Competition

Nobody we found combines the four pieces: a business-owned local agent, a public/private
knowledge graph, owner-approved generative UI on the existing site, and an endpoint for
external assistants. Each piece exists separately, almost always as cloud software. That is a
finding from the sources checked, not proof that no one is building it.

| Who | What they do | Gap against CAC | Take from them |
|---|---|---|---|
| Square | ChatGPT app and Claude plugin since 1 July 2026; food sellers with online ordering are enrolled by default; ordering runs through Cash App with no added marketplace commission | The restaurant is an entry in Square's catalog; ordering only | Tool names and the in-assistant order flow |
| Toast | Orders inside Google's Ask Maps since 6 August 2026 through Toast's own ordering | Google and Toast own the surface | Same |
| OpenTable, Resy, Yelp | Tables bookable inside ChatGPT since 10 August 2026 | The aggregator owns ranking and the guest | The booking request shape |
| Owner.com | Site, ordering, CRM, AI agents; $249–$499/month; $240M raised at $2.3B in August 2026 | Cloud; replaces the site; no agent endpoint announced | Price anchor |
| Slang.ai | Phone AI for restaurants, $399–$599 per location per month | Phone only | Price anchor |
| Microsoft NLWeb | Open source; site chat from schema.org data; each instance is also an MCP server; a basic experimental `/a2a` route | Closest design we found, and it can be self-hosted. It answers from public schema.org data only: no private partition, no approved elements, no owner goals, no agent that learns from unanswered questions | The `ask` tool shape; schema.org-first ingestion |
| Scrunch AXP | Serves an agent-readable copy of a site; from $250/month | Read-only content; no actions, no on-site UI | — |
| Cloudflare, Shopify | WebMCP toggle at the edge; per-store agent endpoints | Plumbing without the business's knowledge or goals | Serving markdown to agents |
| Intercom Fin, Alhena | On-site AI agents, metered per outcome or conversation | Cloud; chat text; support and e-commerce | A per-outcome metric: questions answered without the owner |
| Google A2UI | Open spec for agent-requested UI from a client catalog | A format, not a product | Catalog, surface, action naming |
| UCP (Google, Square, Toast, DoorDash, Uber Eats) | Commerce protocol; the food vertical is listed as coming soon | The incumbents' standard for ordering | Publish a UCP profile once the food vertical ships |

Not checked: generative-UI frameworks as competitors (CopilotKit, Thesys, Vercel AI SDK) and
Yext, Popmenu, BentoBox.

**Where CAC is different**

1. **Ownership.** The endpoint, the goals, and the interface belong to the restaurant.
2. **The long tail.** Ordering protocols cover menus and checkout. Catering quotes, holiday
   hours, a mixed party, private events, and dietary nuance are where a governed graph helps.
3. **One source for both audiences**, with a partition enforced by the database.
4. **It learns from demand.** Every unanswered question becomes a question to the owner.

**Objections to prepare for**

| Objection | Answer |
|---|---|
| Square and Toast already give restaurants agent ordering with no added commission | For ordering, yes, inside their channel. CAC covers what those flows skip and keeps the customer with the owner. It could publish a UCP profile as one more channel once the food vertical ships |
| Why not run NLWeb on the box? | NLWeb is a query layer over public schema.org data. We add the private side enforced by the database, goals that steer answers, approved interactive elements, and an agent that asks the owner what customers could not get answered |
| Why local when menus are public? | Goals, leads, customer notes and the raw visitor log are stored only on the box, and all business-side inference is local. With the local dashboard as owner channel, Flow 1 and Flow 3 run unplugged. No per-conversation meter. The owner keeps the agent if they change platforms |
| Is local cheaper? | Not for inference alone: a cloud API would serve a small site's questions for roughly $15–$35 a month (our estimate at 3,000 questions). The case is ownership, privacy, and an agent that works all day at a flat cost |
| Can one box handle Valentine's Day? | Only new typed questions reach the model, the output is a few dozen tokens, repeats are cached, clicks are free, and when busy it serves presets. Show the measured numbers. More demand means a second box, never a cloud model |
| Will assistants actually call it? | Today the customer adds the connector by URL once. A directory listing is the route to one-click install. Automatic discovery is not shipped by anyone; we say so |
| Standards keep changing | We depend on MCP and MCP Apps, which Claude and ChatGPT both ship. The catalog is our own JSON and maps to A2UI |

## 14. Business model

- **Offer.** A managed appliance: the box, setup from the existing site, and updates.
- **Price.** $299–$499 per month, in the band owners already pay Owner.com, with no commission
  and no per-conversation fee. This is our assumption, not a tested price.
- **Hardware.** Dell lists the 128 GB box at $9,007 (4 TB) and about $6,177 (1 TB) today.
  Press reports put a 64 GB version at $4,999 from 23 October. Prices have risen sharply this
  year, so quote them with a date.
- **Unit economics (assumptions, 3 October 2026).** The 1 TB box at $6,177 is $172 a month
  over 36 months. At $399 a month that leaves about $227 before support, and the hardware is
  paid back in about 16 months. The owner's test: one extra catering order a month (40 covers
  at $25 is $1,000) covers the subscription.
- **Density.** One box can serve a restaurant group or a neighbourhood association, each
  business with its own database and roles, which spreads the hardware cost. Not in v0.
- **Market.** 412,498 independent restaurants in the US at the end of 2025 (Technomic). The
  industry forecasts $1.55 trillion in 2026 sales, and 42% of operators reported being
  unprofitable last year (National Restaurant Association). Start with one city.
- **Beyond restaurants.** The catalog changes per vertical: a salon's booking is the same
  generic form element with a staff field. The graph, partition, and agent do not change.
- **Measuring the other CAC.** The overlay counts leads captured and goal buttons shown and
  clicked. That is how the box will measure acquisition cost; we claim no result yet.

## 15. Demo and pitch

**Lead line.** CAC creates the business's knowledge once and serves it everywhere: as
interface to visitors, as tools to assistants. It keeps learning from what customers ask, and
it never leaves the owner's box.

**Demo (assume three minutes; ask the organizers).** Before going on stage, seed five visitor
questions about gluten-free pasta and twelve about gift cards, and let the agent run: it asks
the owner about the pasta and leaves the gift-card change pending in the inbox. Only one
agent turn then happens live.

| Time | Step |
|---|---|
| 0:00 | The old site. Type "vegetarian options": the list, verified badges, no Add buttons. Type "I want to pick up something vegetarian": same list with Add buttons. The overlay shows one model call each, then none on repeat |
| 0:35 | "Are you open on the 4th of July?" Answer computed by code, with a "Book a table" button: the owner's goal at work. "Do you cater for 40?" The quote form, 40 filled in |
| 1:00 | "Do you have gluten-free pasta?" The agent does not know and says so. Show the owner channel: the agent already asked. The owner replies in one line |
| 1:15 | While the agent records and publishes: the privacy proof. Permission denied as the serving role; the OpenShell policy and a blocked egress attempt; the canary result |
| 1:50 | Ask again. Now it answers, "Confirmed by the restaurant". No code changed |
| 2:00 | The graph evolves. The inbox shows a pending change: "12 visitors asked about gift cards. I created a GiftCard type, two options, and a request form." The owner taps approve. Ask "do you sell gift cards?": a list and a form appear. No code changed, nothing restarted |
| 2:25 | If built: Claude asks the two-friends question and the restaurant's own element renders in Claude. Otherwise its recording, or one sentence of roadmap |
| 2:40 | Unplug the network. Flow 1 still answers. Overlay: model host is the box, leads captured, cache hits |

**How the build maps to the rubric (as the team understands it)**

| Criterion | What we show |
|---|---|
| Local | All inference, graph, and agent on the box; the Serve API refuses to start unless the model host is local; OpenShell blocks other egress; Flow 1 and Flow 3 run unplugged with the local dashboard as owner channel |
| Technical | An agent that changes the graph's structure at run time with no migration or restart; constrained selection with code-written facts; database-enforced partition with allowlisted publish; measured latency and concurrency |
| Business value | The site grows new capabilities from customer demand (gift cards appeared because people asked); owner goals in every answer; leads captured and counted; the long tail platforms skip |
| Pitch | The lead line, then WIMP to CAC and "aimed at your other CAC", then two live loops: unknown to answered, and unasked-for to built |

**Claims to correct before pitching**

| Do not say | Say instead |
|---|---|
| Shopify will stop merchants pulling their own data in December | Since 1 January 2026 new custom apps can no longer be created in the Shopify admin. Existing ones keep working; new ones are built in Shopify's Dev Dashboard, where own-store access uses tokens that expire after 24 hours. Merchants can still read their own data. The weaker point stands: the platform sets the terms for reaching your own data |
| Restaurants are invisible to AI agents | Platforms have made restaurants orderable inside assistants; the restaurant is a row in their catalog |
| Claude finds our agent from the website | The customer adds the restaurant's connector once |
| It is cheaper than cloud | It is owned, private, and unmetered |
| A bigger deployment would fall back to a cloud model | When the box is busy it serves cached and preset answers; more demand means a second box |
| The box costs about $4,000 | About $6,200 to $9,000 today for 128 GB; press reports put a 64 GB model at $4,999 from 23 October |
| ADUI | A2UI (Google's spec); ours is an A2UI-style catalog |
| AI referrals convert 60% better | True for US retail sites (Adobe, July 2026). Say it is retail data |
| It lowers customer acquisition cost | It is aimed at it, and it measures leads and goal clicks. No result yet |
| Square's and Toast's AI ordering is built on UCP | Square's runs through Cash App ordering and Toast's through its own ordering. Both co-develop UCP's food vertical, which is listed as coming soon |
| The box does 97 (or 2,776) tokens a second | One blog measured 97 single-stream; another measured 21. 2,776 is batched total throughput for an 8B model. Quote our own measurement |

## 16. Build plan

Written for a 9:00 PM deadline with building from 2:00 PM. If the deadline is 10:00 PM, the
extra hour goes to Flow 2. A is the box and agent, B is the graph and pipeline, C is surfaces.

| Clock | A: box and agent | B: graph and pipeline | C: surfaces |
|---|---|---|---|
| 2:00–3:00 | First-30-minute checks. One OpenClaw agent sends "hello" on the owner channel. Benchmark a standalone selection function on the 30 fixture intents at 1 and 4 concurrent | Postgres, DDL, roles. Load the seed, publish. Stub `/v1/intent` that serves the golden surface fixtures | Static demo site from the same seed. Widget shell against the stub. 15 minutes on a hello-world MCP connector through the tunnel: go or no-go for Flow 2 |
| 3:00–5:00 | Owner tools API: read endpoints, `POST /owner/changes` with tiers, owner-only approve and revert. Agent loop against a seeded fake gap and a seeded gift-card topic | Real pipeline: slots, retrieval, selection, validator, binder, exact cache, logging | Five components, the three generic ones, plus `AllergenNotice` and `GoalCTA` from fixtures. Presets. Forms to leads. Cart count |
| **5:00 gate** | Both loops run on the box against seeded topics (gap answered; gift-card type created and pending), else apply cut line 3 now | `/v1/intent` passes 27 of 30 fixtures | Widget renders every fixture |
| 5:00–6:30 | Loops on real topics. Tagging and edits. OpenShell policy file, blocked-egress script, recovery script. Digest | Verified-only rules, steer, canary and permission scripts, metrics, pre-warm on publish | Owner inbox page with approve, reject, confirm and revert. Chips, overlay, busy and error states |
| **6:30 gate** | Flow 1 and Flow 3 pass acceptance. Only then start Flow 2 | | |
| 6:30–7:30 | Load test at 1, 4, 8, once with an agent turn in flight | Data quality. JSON-LD ingest if time | Flow 2: text-only `ask_restaurant`, then the MCP App. If the gate failed, help close P0 |
| 7:30–8:00 | Record every flow as backup | | |
| 8:00 | Freeze. Rehearse twice. Submit through BuilderBase by 8:45 | | |

**First 30 minutes (these decide the day)**

1. Ask an organizer: the deadline in Eastern time, what the submission needs (repo, video,
   deck), how long the demo slot is, and open questions 3 and 4 below.
2. `curl` the local model endpoint: the model answers, and a structured-output call is valid
   with thinking off.
3. Time one agent turn with one tool call. Write the seconds into Flow 3.
4. An embedding model is on disk and returns a vector; record its length and set it in the
   DDL. If none, switch to the full-text fallback now.
5. With the model server, embedder and Postgres running, at least 16 GB of memory is free.
6. The pgvector image starts; Python and Node dependencies install.
7. The sandboxed agent can reach the Owner tools API, and the owner channel delivers a message.
8. A hello-world MCP server with a static UI resource renders in Claude through the tunnel, on
   an account that allows custom connectors.
9. Decide the vLLM concurrency setting now.

**Cut lines, in order**

1. Flow 2 is not started unless the 6:30 gate passes. If the MCP App does not render, ship
   text-only `ask_restaurant` and show the element in the local MCP Apps test host.
2. Tunnel blocked by the venue network: phone hotspot; failing that, demo Flow 2 from the
   local test host and say why.
3. Agent loop not running by 5:00: keep the Owner tools API and inbox as built, and reduce
   the agent to two jobs: ask the owner about the top gap, and propose one structural change
   (the gift-card type and form). Drop tagging and edits from the live demo.
4. Sandboxed agent cannot reach the Owner tools API over plain HTTP: register the same
   endpoints as a Streamable HTTP MCP server with NemoClaw, which is the tool path it
   documents.
5. Local dashboard not reachable from a phone: use a messaging channel and say on stage that
   the owner chose it.
6. Structured output unreliable on one backend: switch backend, keep the validator and one
   retry.

## 17. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Less time than planned (deadline is 9 or 10 PM) | High | Clock-based plan, two gates, Flow 2 behind the second gate |
| NemoClaw setup eats hours (alpha; 30–60 min first install; no auto-restart) | High | One person owns it from the first minute; scripted recovery; one agent, one job |
| Judges read the direct model path as bypassing the required stack | Medium | Ask a mentor early; present it as a security decision; Plan B in section 11 |
| A cloud assistant in the demo read as "not fully local" | Medium | Frame it as the customer's assistant; end the demo unplugged; have the recording |
| The agent makes a poor structural change (a junk type, a wrong tag) | Medium | Balanced autonomy: structure waits for one tap; tags show as unverified; every change has a reason and a revert |
| The self-evolving loop takes the time Flow 2 needed | High | Accepted: the loop is P0, Flow 2 is behind the 6:30 gate and has a recording fallback |
| Model picks the wrong component | Medium | Tiny catalog, `use_when` lines, 30-intent fixture with a pass mark, busy fallback |
| Agent turn too slow for a live demo | Medium | Measure in the first 30 minutes; pre-ask the owner before going on stage |
| Publish empties the cache mid-demo | Certain | Pre-warm on publish (P0) |
| Embedding model missing on the box | Medium | Full-text fallback behind the same function |
| Live network failure on stage | Medium | Recordings of every flow; Flow 1 and Flow 3 work with no internet |
| Wrong allergen information | Low, high impact | Verified-only badges; no safe lists; fictional restaurant; notice component |

## 18. Open questions

**Ask organizers or a mentor now**

1. What is the exact submission deadline in Eastern time, and what must be submitted?
2. Is there a written rubric? Is there a scoring bonus for smaller teams, as in San Francisco?
3. Must every model call pass through the OpenClaw agent, or may a local service call the same
   local model directly?
4. The series rule says the agent "runs locally on the box (no cloud API)". May a cloud
   assistant appear in the demo as the external customer's agent?
5. What is preinstalled on the box (NemoClaw, which model weights, an embedding model)?
6. How long is the demo slot?

**Decided here; change if you disagree**

1. The demo restaurant is fictional, to avoid real allergen claims about a real business.
2. The owner channel is the local OpenClaw dashboard; a messaging app is optional.
3. The agent's autonomy setting is balanced: tags and links publish at once marked
   unverified; new types, props, elements, facts and edits wait for one owner tap. Switch to
   free if you want everything to publish without a tap.
4. The self-evolving loop is P0 and takes priority over the Claude flow.

## 19. Ideas to build on

| Idea | Helps with | Effort today | What to build |
|---|---|---|---|
| Demand report | Business value | 1 h | Digest from top topics, open gaps, and leads per element: "37 asked about gluten-free, 0 tagged dishes; 5 booking requests this week" |
| Onboarding interview | Business value | 1 h | Completeness check after ingest; one batched message of what is missing |
| Slot-masked cache | Local, technical | 30 min | "Open on <any date>" costs one model call ever |
| Confirmed-by-owner mark | Pitch | 30 min | "Confirmed by the restaurant, 3 Oct" on answers and in the text assistants read. Hypothesis: assistants may come to prefer sources that state provenance |
| "Add to Claude" button on the site | Pitch | 30 min | The connector URL on the page: the nearest honest version of "Claude finds the site's agent" |
| Voice | Local | 1–2 h, only if a speech model is already on the box | The wireframe's microphone, with local speech recognition |
| Roadmap, talk only | — | — | Agent-to-agent negotiation (the assistant asks for six at 7:00; the agent offers 6:30 and the prix fixe), WebMCP tools for browser agents, per-vertical catalogs, UCP profile |

## 20. Sources

Hackathon and stack

- Event page: https://builderbase.com/event/dell-x-nvidia-ai-hackathon-boston
- Series rules (other cities): https://luma.com/dellxnvdia-hackathon , https://events.cornell.edu/event/dell-x-nvidia-ai-hackathon , https://gtedge.ai/event/dell-x-nvidia-hackathon-local-ai-on-dell-pro-max-with-gb10-new-york-ny/
- NemoClaw architecture: https://docs.nvidia.com/nemoclaw/latest/reference/architecture.html
- NemoClaw release notes: https://docs.nvidia.com/nemoclaw/latest/about/release-notes.html
- NemoClaw scope (one trusted operator): https://docs.nvidia.com/nemoclaw/user-guide/openclaw/about/overview.md
- Sub-agents share a sandbox: https://docs.nvidia.com/nemoclaw/user-guide/openclaw/configure-agents/set-up-sub-agent.md
- Heartbeats: https://docs.nvidia.com/nemoclaw/user-guide/openclaw/configure-agents/configure-agent-heartbeats.md
- Managed MCP servers (NemoClaw is a client only): https://docs.nvidia.com/nemoclaw/user-guide/openclaw/manage-sandboxes/mcp-servers/about-managed-mcp-servers
- vLLM defaults on Spark: https://docs.nvidia.com/nemoclaw/user-guide/openclaw/inference/local-inference/set-up-vllm
- NVIDIA tutorial (30–90 s, prompt injection note): https://developer.nvidia.com/blog/build-a-secure-always-on-local-ai-agent-with-nvidia-nemoclaw-and-openclaw/
- GB10 throughput: https://rikkarth.com/blog/2026-04-23-benchmark-results-for-qwen-qwen3-6-35b-a3b-fp8-nvidia-dgx-spark-gb10-serving-via-vllm , https://llmrequirements.com/news/2026-06-03-nvfp4-qwen-3-6-35b-dgx-spark
- vLLM structured outputs: https://docs.vllm.ai/en/latest/features/structured_outputs/

Protocols

- Claude web fetch limits: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool
- Custom connectors: https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- MCP Apps quickstart: https://claude.com/docs/connectors/building/mcp-apps/quickstart
- MCP Apps spec: https://modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp
- MCP Apps in ChatGPT: https://developers.openai.com/apps-sdk/mcp-apps-in-chatgpt
- A2UI: https://a2ui.org/
- A2A: https://a2a-protocol.org/latest/specification/

Graph and safety

- pgvector: https://github.com/pgvector/pgvector
- Postgres row security and roles: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- Text-to-Cypher with small models: https://aclanthology.org/2025.emnlp-industry.133.pdf
- schema.org MenuItem: https://schema.org/MenuItem
- FDA allergens: https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/food-allergies
- Massachusetts allergen notice: https://www.law.cornell.edu/regulations/massachusetts/105-CMR-590-011

Generative UI and UX

- Google generative UI paper: https://generativeui.github.io/static/pdfs/paper.pdf
- NN/g, intent-based interfaces: https://www.nngroup.com/articles/ai-paradigm/
- AI crawlers and JavaScript: https://vercel.com/blog/the-rise-of-the-ai-crawler

Competition and market

- Square: https://squareup.com/us/en/press/claude-chatgpt-integrations
- Toast in Ask Maps: https://finance.yahoo.com/technology/ai/articles/arriving-now-ai-powered-toast-123000618.html
- ChatGPT bookings: https://www.androidauthority.com/chatgpt-restaurant-reservations-and-waitlists-3696712/
- Owner.com funding and pricing: https://www.prnewswire.com/news-releases/owner-raises-240m-led-by-goldman-sachs-alternatives-to-build-the-ai-native-platform-for-every-local-business-302862420.html , https://www.owner.com/pricing
- Slang.ai pricing: https://www.slang.ai/pricing
- Intercom pricing: https://www.intercom.com/pricing ; Alhena pricing: https://alhena.ai/pricing
- NLWeb: https://github.com/nlweb-ai/NLWeb
- Scrunch pricing: https://scrunch.com/pricing
- Cloudflare WebMCP: https://blog.cloudflare.com/webmcp/
- Shopify store endpoints: https://shopify.dev/docs/apps/build/storefront-mcp
- UCP: https://ucp.dev/
- Amsterdam restaurant test: https://dev.to/blondedevrules/we-built-an-mcp-server-so-any-assistant-can-book-a-table-2le3
- BrightLocal survey: https://www.brightlocal.com/research/local-consumer-review-survey/
- Adobe AI referral data: https://www.digitalcommerce360.com/2026/08/19/adobe-ai-referral-traffic-data-july-2026/
- Technomic independents: https://www.nrn.com/independent-restaurants/the-independent-restaurant-sector-shrunk-by-2-3-in-2025
- National Restaurant Association forecast: https://restaurant.org/research-and-media/media/press-releases/persistent-cost-increases-and-enduring-demand-will-shape-the-restaurant-industry-in-2026/
- DoorDash commissions: https://merchants.doordash.com/en-us/products/marketplace
- Dell pricing: https://www.dell.com/en-us/shop/desktop-computers/spd/dellpromaxwithgb10fcm1253
- 64 GB model price: https://hothardware.com/news/nvidia-dgx-spark-64gb-release
- Cloud API pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Shopify custom apps change: https://changelog.shopify.com/posts/legacy-custom-apps-can-t-be-created-after-january-1-2026
- Shopify own-store tokens: https://shopify.dev/docs/apps/build/authentication-authorization/client-credentials-grant
