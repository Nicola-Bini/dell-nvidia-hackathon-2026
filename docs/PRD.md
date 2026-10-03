# CAC — Product Requirements Document

| | |
|---|---|
| Working title | CAC: Chats, Agents, Context |
| Event | Dell x NVIDIA AI Hackathon, Boston, 3–4 October 2026 |
| Challenge | "Ship an always-on AI agent running fully local on the Dell Pro Max with GB10" |
| Status | Draft v1, written 3 October 2026 from the whiteboard session and verified web research |
| Companion | [SCHEMA.md](SCHEMA.md): database, catalog, and wire contracts for scaffolding |
| Research | [research/](research/README.md): the six fact-checked research reports behind this document |

## 1. Summary

CAC is a local agent that a small business owns. It turns the business's existing website into
a knowledge graph, then serves that knowledge two ways from one box:

1. **To people on the website.** A visitor types what they want. The agent answers with
   owner-approved interface elements (a filtered menu, a booking form, a catering quote form)
   instead of a wall of chat text. Clicks follow fixed paths with no model call.
2. **To AI assistants acting for customers.** Claude or ChatGPT asks the restaurant's agent
   directly and gets the same governed answer, including an interactive component.

Behind both, an always-on agent keeps the graph current, notices what customers ask that the
business cannot answer, and asks the owner. Private data never crosses to the public side,
because the serving processes have no database access to it.

The name is the pitch: WIMP (windows, icons, menus, pointers) made the business guess what
visitors want. CAC (chats, agents, context) lets the visitor say it. It also lowers the other
CAC, customer acquisition cost, by steering every answer toward the owner's goals.

### Three changes from the whiteboard, forced by research

| Whiteboard plan | What research found | Decision |
|---|---|---|
| Claude visits the site and is redirected to an A2A endpoint | No consumer assistant speaks A2A to arbitrary sites. Claude's web fetch cannot call URLs it composes and cannot POST. Claude and ChatGPT do render MCP Apps from a connected MCP server. | Flow 2 is an MCP server with an MCP Apps component, added to Claude as a custom connector. A2A agent card is a secondary adapter. |
| The local LLM builds the UI | Free-form UI generation is a frontier-model capability. Small models are reliable when constrained to pick a named component and ids. | The model returns a component name plus node ids under a JSON-schema constraint. Code fills in every fact. |
| Every request goes through the NemoClaw agent | Agent loops are slow and prefill-heavy; NVIDIA's own tutorial quotes 30–90 s per response with the 120B model. NemoClaw's gateway is not designed to face anonymous visitors. | The visitor path is a thin local service calling the same local model directly. NemoClaw runs the always-on agents: graph upkeep, gap detection, owner conversation. |

## 2. Hackathon constraints

| Fact | Source and confidence |
|---|---|
| Runs 3–4 October, listed as 2:00 PM to 2:00 AM | Event page. One researcher read the listing as UTC, which would be 10 AM to 10 PM Eastern. **Confirm the submission deadline with organizers.** |
| Must run fully local on the Dell Pro Max with GB10; first prize is the box | Event page |
| Required stack is OpenClaw + NVIDIA NemoClaw + OpenShell; demo on the provided box; submit through BuilderBase; top 8 pitch live | Pages for the other cities in this series (SF, Seattle, NYC, Cornell). Not stated on the Boston page. |
| Judging 25% pitch, 25% local, 25% business value, 25% technical | The team's understanding. Not published anywhere we could find. |
| "A real business or corporate workflow, not a toy demo" | Cornell page for the same series |
| Venue Wi-Fi is not enough for model downloads | NYC page for the same series |

Hardware: GB10 Grace Blackwell, 128 GB unified memory, DGX OS 7. NemoClaw is alpha software
(v0.0.130 on 1 October 2026) and installs by script; it is not part of DGX OS.

## 3. Problem

**For the owner.** A restaurant's knowledge lives in a site built for browsing: a PDF menu,
an hours table, a contact form. The owner pays platforms to reach customers (Owner.com is
$249/month plus 5% per order or $499/month flat; DoorDash takes 15–30% on delivery) and the
platform, not the owner, holds the customer relationship.

**For the visitor.** The site makes them hunt. "Which dishes are vegetarian?", "are you open
on the 4th?", and "do you cater for 40?" each mean scanning pages or calling.

**For AI assistants.** 45% of US consumers used generative AI for local business
recommendations in 2026, up from 6% in 2025 (BrightLocal, n=1,002). Assistants read sites
badly: major AI crawlers do not run JavaScript, and a study of 200 Amsterdam restaurants found
only 16 could be taken to the final booking step by a browser agent, with none of 163 working
sites exposing an interface an assistant could call. Restaurant brands show up in Google's local
3-pack 24.3% of the time but in ChatGPT recommendations 5.3% (SOCi; multi-location brands).

**The gap in current answers.** Square, Toast, OpenTable, Resy and Yelp already put restaurants
inside ChatGPT, Claude and Google Maps. In each case the restaurant is a row in the platform's
catalog and the platform owns ranking and the guest. Nobody we found gives the owner their own
agent, on their own hardware, answering both people and assistants from one governed source.

## 4. Product principles

1. **The owner owns the agent.** The box, the graph, the goals, and the approved interface
   belong to the business.
2. **One graph, two audiences.** People and assistants get the same facts from the same place.
3. **Typed intent goes to the model; clicks never do.** Buttons, forms, carts, and navigation
   are fixed paths.
4. **The model picks, code fills.** The model chooses a component and node ids. Prices, hours,
   and diet badges come from the graph.
5. **Private by structure.** Serving code cannot read private data. This is a database
   permission, not an instruction in a prompt.
6. **Every answer leans toward an owner goal**, and never at the cost of answering the question.
7. **Keep the existing site.** CAC is an added panel. Owners keep editing their site the way
   they already do.

## 5. Users

| User | Wants | CAC gives them |
|---|---|---|
| Owner | More bookings and catering leads, less platform dependence, no new dashboard to learn | An agent that reads their site, asks them only what it cannot find, and steers toward their goals |
| Site visitor | A fast answer and the next step | An intent box that returns the right element, with the nav bar still there |
| Customer's AI assistant | Structured, trustworthy facts and an action it can take | A tool endpoint with verified data and a booking request flow |

## 6. Scope

**P0: must work in the demo**

- Knowledge graph for one demo restaurant, ingested from its site, with public/private
  partition and a publish step.
- Flow 1: website panel with intent box, component rendering, deterministic actions, navigation
  presets, exact-match cache.
- Flow 3: always-on NemoClaw agent that turns unanswered questions into a question for the
  owner, records the owner's answer as verified, and republishes.
- Privacy proof: canary leak test and a blocked egress attempt shown live.
- Live metrics: latency, cache hits, in-flight requests, "cloud calls: 0".

**P1: build in parallel, cut if blocked**

- Flow 2: MCP server plus MCP Apps component in Claude via custom connector.
- Refinement ("only desserts") against the current surface.
- Semantic cache and cache pre-warming by the agent.
- Cart and pickup order as a lead (no payment).
- Review highlights component.

**P2: mention as roadmap**

- A2A agent card and OpenClaw's A2A channel. Agent-proposed new components with owner approval.
  Voice input. Onboarding a real site live. WebMCP tool registration. UCP profile for ordering.
  Multi-box clustering.

**Non-goals**

- Payments. Rebuilding the owner's site. An owner dashboard. Multi-tenant hosting. Any cloud
  model call from the business side. Confirmed reservations (we create requests).

## 7. Experience

### Flow 0: Onboarding

1. The owner gives the site URL.
2. Ingestion reads structured data first (schema.org JSON-LD), then page text, then PDF and
   image menus, and extracts typed nodes with provenance.
3. Extracted nodes are drafts. Facts taken from the owner's own public site are marked public
   and approved in bulk; diet and allergen claims stay unverified until the owner confirms.
4. The owner states goals in plain words ("more weeknight bookings", "sign up catering
   clients"). These become private Goal nodes.
5. Publish. The owner adds one script tag to the site.

Acceptance: from a clean database, one command ingests the demo site and publishes a graph
with at least 30 menu items, hours, location, two services, and two goals.

### Flow 1: Visitor on the website

Layout (from the wireframe): the existing header and nav stay. The panel has a history rail on
the left (earlier intents as chips), the current surface in the centre, and the intent box with
suggested chips at the bottom.

| Visitor does | Result | Model call |
|---|---|---|
| Types "vegetarian options" | `MenuList` of vegetarian dishes with verified badges, no cart button (they want to know, not order), allergy notice, "Book a table" CTA | yes, once; cached after |
| Types "I want to order pickup, vegetarian" | Same list with "Add" buttons | yes |
| Types "only desserts" | Current list filtered to desserts | yes (P1) |
| Types "are you open on the 4th of July?" | `HoursCard` with the answer computed from hours data, plus booking CTA | yes, to route; the answer is code |
| Types "do you cater?" | `CateringQuoteForm` asking headcount and date | yes |
| Types "do you have gluten-free pasta?" (unknown) | "We haven't confirmed that yet, please ask staff", contact option; logged as a gap | yes |
| Clicks nav "Menu" | Preset menu surface | no |
| Clicks "Add", "Book a table", submits a form | Cart update, preset form, lead stored | no |
| Asks the same thing a second time, or a second visitor asks | Instant answer | no (cache) |

Acceptance:

- Uncached typed intent returns in under 2.5 s at median on the box; cached in under 200 ms;
  click actions in under 100 ms.
- Every rendered price, hour, and badge matches the graph.
- An unverified diet or allergen claim is never shown as fact.
- The same question asked twice produces one model call.

### Flow 2: A customer's assistant

1. The customer has the restaurant's connector in Claude. They ask: "Dinner tonight in
   Cambridge. One friend is vegetarian, one loves meat."
2. Claude calls `ask_restaurant`. The MCP server on the box runs the same intent pipeline over
   the public graph.
3. Claude receives text built from graph facts, plus the surface, and renders the restaurant's
   own component inline.
4. The customer taps "Request a table". The component calls `request_booking` directly. The
   lead lands on the box.

What is true today, to say plainly to judges: the customer adds the connector once. No
assistant discovers a business's agent from its URL on its own yet. MCP and MCP Apps are the
standards; the graph, the partition, and the component selection are ours.

Acceptance: from Claude, a question returns a rendered component with correct data; a booking
request creates a lead; asking for customer names returns nothing private.

### Flow 3: The always-on loop

1. On a heartbeat, the Gardener agent reads new intents, groups unanswered ones, and drafts
   proposals (a missing FAQ, a diet tag, a likely new component).
2. The Liaison agent messages the owner: "Six visitors asked about gluten-free pasta this
   week. I have nothing verified. What should I tell them?"
3. The owner replies in plain words. The agent writes an owner-verified node, publishes, and
   pre-warms the cache for that question.
4. The next visitor gets the answer.

Acceptance: an unanswered question at minute 0 is answered correctly for the next visitor
after one owner reply, with no code change and no restart.

## 8. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| G1 | Ingest a site into typed nodes and edges with source, extractor, and verification status | P0 |
| G2 | Label registry marks which node types may ever be public | P0 |
| G3 | `publish()` copies only approved public nodes into the serving store and bumps a graph version | P0 |
| G4 | Retrieval is vector entry plus fixed expansion; the model never writes a query | P0 |
| G5 | Diet and allergen facts render only when owner-verified; otherwise "not verified, ask staff" | P0 |
| S1 | `POST /v1/intent` returns a surface built from approved components | P0 |
| S2 | Model output is constrained to approved components and retrieved node ids, then validated | P0 |
| S3 | `GET /v1/view/{preset}` and `POST /v1/action` never call the model | P0 |
| S4 | Exact cache keyed on normalized text, slots, and graph version | P0 |
| S5 | Semantic cache requiring identical slots (date, number, negation) | P1 |
| S6 | Binder appends an allergy notice and at most one goal CTA | P0 |
| S7 | When the queue is full, serve the nearest cached surface or a preset; never call a cloud model | P1 |
| W1 | One script tag adds the panel as a sandboxed iframe on the existing site | P0 |
| W2 | Six P0 components render from surface JSON | P0 |
| W3 | History rail and suggested-intent chips | P0 |
| W4 | Theme from BrandTrait nodes (colours, tone) | P1 |
| A1 | Gardener agent runs on a heartbeat and writes drafts and gaps only | P0 |
| A2 | Liaison agent asks the owner and records verified answers | P0 |
| A3 | Agents run inside the NemoClaw sandbox with default-deny egress | P0 |
| A4 | Agents pre-warm the cache with the most common intents | P1 |
| A5 | Agents propose new components for owner approval | P2 |
| X1 | MCP server exposes profile, ask, booking request, catering quote | P1 |
| X2 | `ask_restaurant` returns an MCP Apps component built from the same bundle as the widget | P1 |
| X3 | A2A agent card with the same skills | P2 |
| O1 | `/v1/metrics` and an on-screen overlay for latency, cache, in-flight, graph version | P0 |
| O2 | Canary leak test runs against every public endpoint | P0 |
| O3 | Load test script reports p50 and p95 at 1, 4, and 8 concurrent intents | P0 |

## 9. Privacy and safety

**Invariants**

1. The serving role (`cac_serve`) has no grant on the private schema. A prompt injection that
   fully controls the model still cannot read a customer record, because the process holding
   the model's output has no path to that data.
2. The model's output can only name node ids that were retrieved from the public store for
   that request.
3. Goals are private. The serving side sees a number (steer weight) per component, not the
   goal text.
4. Visitor text and leads are written to tables the serving role can insert into but not read.
5. Card numbers, SSNs, and licence numbers are never stored anywhere in CAC.

**Why not rely on the sandbox for this.** NemoClaw sub-agents share one sandbox and its docs
say file permissions do not isolate them from each other; NVIDIA also notes no sandbox fully
stops prompt injection. The sandbox limits what agents can reach on the network. The database
role limits what the public side can read. The demo shows both.

**Food safety.** The FDA lists nine major allergens and sets no safe threshold; schema.org has
no allergen property. So allergen and diet edges carry `verified_by_owner`. Unverified claims
render as "not verified, please ask staff". The model never writes an allergen statement.
Massachusetts requires menus to carry a notice asking customers to tell their server about
allergies (105 CMR 590.011(C)(2)); the `AllergenNotice` component carries that text.

**Proof in the demo**

- A fake customer with a unique name sits in the private graph. The test asks every endpoint,
  including through Claude, to reveal it. It never appears.
- The agent tries to reach a non-allowlisted host and OpenShell blocks it on screen.

## 10. Architecture

```
  Visitor's browser                         Customer's assistant (Claude, ChatGPT)
  existing site + script tag                custom connector: MCP + MCP Apps
          |                                              |
==========|================ LAN / tunnel ================|=========================
          v                                              v
   Widget (React, iframe) ---> Serve API <------- MCP server (public tools)
                                 |    |
                  role cac_serve |    +---> Local model server (vLLM), JSON-constrained
                                 v
        Postgres + pgvector:  kg_public  <--- publish() ---  kg (full graph)  +  ops
                                                                   ^
                                                    role cac_owner |
   NemoClaw + OpenShell sandbox                                    |
   OpenClaw agents: Gardener, Liaison  ----->  Owner tools API ----+
          |                                    (localhost only)
          +--- Telegram or local dashboard ---> Owner

  Everything below the double line runs on the Dell Pro Max with GB10.
```

| Component | Job | Notes |
|---|---|---|
| Widget | Intent box, renders surfaces, runs client actions | One React bundle, also built as a single HTML file for the MCP App |
| Serve API | Intent pipeline, presets, actions, metrics | Python service; connects as `cac_serve` |
| Model server | One constrained completion per uncached intent | vLLM with structured outputs; the same endpoint NemoClaw uses |
| Embedder | Embeds nodes and intents | Small local model already on the box |
| Postgres + pgvector | Graph, public projection, runtime tables | One container; schemas and roles in SCHEMA.md |
| Owner tools API | Drafts, gaps, owner answers, publish | Localhost only; connects as `cac_owner` |
| NemoClaw agents | Always-on upkeep and owner conversation | OpenClaw agents in an OpenShell sandbox, heartbeat-driven |
| MCP server | Public tools for assistants | Separate process (NemoClaw does not host listeners); TypeScript, copied from Anthropic's quickstart versions |
| Ingestion job | Site to drafts | Structured data first, then page text, then PDF and image menus |

**Where NemoClaw is load-bearing.** The challenge is an always-on agent, and the series
requires this stack. In CAC the agents are what make the product learn: without the Gardener
and Liaison, the graph is a static export. The visitor path uses the same local model but skips
the agent loop for speed. Ask a mentor early whether that split is acceptable (section 15).

**Model choice.** Use what is already on the box; do not download at the venue.

| Use | Model class | Why |
|---|---|---|
| Visitor intents | 30–35B mixture-of-experts at NVFP4 on vLLM (NemoClaw's Spark default is `nvidia/Qwen3.6-35B-A3B-NVFP4`; a Nemotron 3.5 Lightning 30B profile exists, marked experimental) | Reliable structured output; thinking disabled; under 60 output tokens |
| Ingestion and Gardener | Largest model that fits, run in the background | Extraction quality rises with model size and latency does not matter |
| Embeddings | `qwen3-embedding:0.6b` or `bge-m3` via Ollama | Already supported locally; the graph is a few hundred nodes |

**Capacity.** Output tokens are the latency budget, so the selection is kept tiny. Published
single-stream speeds for this class on the GB10 range from 21 tokens/s (FP8) to about 97
(NVFP4), which puts a 40–60 token selection at roughly 1–3 s. NemoClaw's managed vLLM defaults
to 4 concurrent sequences; raise it to 8 or more. Our estimate, to be replaced by measurement:
1–2 uncached intents per second per box. Clicks and cache hits cost nothing, so that supports
hundreds of people browsing at once. When the queue is full, CAC serves the nearest cached
surface or the preset; it does not call a cloud model. Beyond one box, DGX Spark systems
cluster.

**Hosting.** There is no cloud deployment. The only external pieces are the tunnel that lets
assistants reach the MCP server and the owner's messaging channel.

## 11. Data and schema

Full definitions are in [SCHEMA.md](SCHEMA.md). In short:

- Typed nodes and edges in Postgres, each with visibility, status, provenance, and owner
  verification.
- Public: business, location, hours, menu, items, ingredients, diets, allergens, services,
  FAQs, review summary, brand traits, UI components, intents, actions.
- Never public: goals, knowledge gaps, proposals, customers, owner notes, leads, raw intent
  log.
- "Vegetarian" is a node, not a column. Items connect to it. Asking for vegetarian finds the
  node by vector search and follows its edges, which is the design from the whiteboard.
- UI components and intents are also nodes, so retrieval returns both the data and the
  component that should show it.

## 12. Competition

Nobody we found combines the four pieces: a business-owned local agent, a public/private
knowledge graph, owner-approved generative UI on the existing site, and an endpoint for
external assistants. Each piece exists separately, almost always as cloud software. That is a
finding from the sources checked, not proof that no one is building it.

| Who | What they do | Gap against CAC |
|---|---|---|
| Square | ChatGPT app and Claude plugin since 1 July 2026; food sellers with online ordering are enrolled by default, ordering runs through Cash App | The restaurant is an entry in Square's catalog; ordering only |
| Toast | Orders inside Google's Ask Maps since 6 August 2026 through Toast's own ordering | Same; Google and Toast own the surface |
| OpenTable, Resy, Yelp | Tables bookable inside ChatGPT since 10 August 2026 | The aggregator owns ranking and the guest |
| Owner.com | Site, ordering, CRM, AI agents; $499/month; $240M raised at $2.3B in August 2026 | Cloud; replaces the site; no agent endpoint announced |
| Slang.ai | Phone AI for restaurants, $399–$599 per location per month | Phone only |
| Microsoft NLWeb | Open source; site chat from schema.org data, and each instance is also an MCP server | Closest design. No private partition, no approved UI catalog, no owner goals, not local |
| Scrunch AXP | Serves an agent-readable copy of a site; from $250/month | Read-only content; no actions, no on-site UI |
| Cloudflare, Shopify | WebMCP toggle at the edge; per-store agent endpoints | Plumbing without the business's knowledge or goals; products, not restaurants |
| Intercom Fin, Alhena | On-site AI agents, metered per outcome or conversation | Cloud; chat text; support and e-commerce |
| Google A2UI | Open spec for agent-requested UI from a client catalog (v0.9.1; v1.0 candidate) | A format, not a product. We adopt its vocabulary |
| UCP (Google, Square, Toast, DoorDash, Uber Eats) | Commerce protocol; the food vertical is listed as coming soon | The incumbents' standard for ordering. CAC should publish a UCP profile later, not compete |

**Where CAC is different**

1. **Ownership.** The endpoint, the goals, and the interface belong to the restaurant.
2. **The long tail.** Ordering protocols cover menus and checkout. Catering quotes, holiday
   hours, a mixed party, private events, and dietary nuance are where a governed graph helps.
3. **One source for both audiences**, with a partition that holds under prompt injection.
4. **It learns from demand.** Every unanswered question becomes a question to the owner.

**Objections to prepare for**

| Objection | Answer |
|---|---|
| Square and Toast already give restaurants agent ordering for free | For ordering, yes, inside their channel. CAC covers what those protocols skip and keeps the customer with the owner. It can publish to UCP as one more channel. |
| Why local when menus are public? | Goals, leads, customer notes, and visitor questions are not public, and they stay on the box. No third-party chat vendor holds transcripts. No per-conversation meter. The owner keeps the agent if they change platforms. |
| Is local cheaper? | Not for inference alone. A cloud API would serve a small site's questions for under $30 a month. The case is ownership, privacy, and an agent that works all day at a flat cost. |
| Can one box handle Valentine's Day? | Only new typed questions reach the model, answers are about 50 tokens, repeats are cached, clicks are free. Show the measured numbers. |
| Will assistants actually call it? | Today the customer adds the connector. That is the same step as installing any Claude or ChatGPT app. Automatic discovery is not shipped by anyone; we say so. |
| Standards keep changing | We depend on MCP and MCP Apps, which Claude and ChatGPT both ship. The catalog is our own JSON and maps to A2UI. |

## 13. Business model

- **Offer.** A managed appliance: the box, setup from the existing site, and updates.
- **Price.** $299–$499 per month, in the band owners already pay Owner.com and reservation
  platforms, with no commission and no per-conversation fee. This is our assumption, not a
  tested price.
- **Hardware cost.** Dell lists the 128 GB box at $9,007 (4 TB) and about $6,177 (1 TB) today;
  a 64 GB version at $4,999 is announced for 23 October. Prices have risen sharply this year,
  so quote them with a date.
- **Market.** 412,498 independent restaurants in the US at the end of 2025 (Technomic). The
  industry forecasts $1.55 trillion in 2026 sales and 42% of operators reported being
  unprofitable last year (National Restaurant Association). Start with one city.
- **Beyond restaurants.** The catalog changes per vertical (a salon's booking form needs a
  staff picker); the graph, partition, and agents do not.

## 14. Demo and pitch

**Three-minute demo**

1. The old site. Ask the audience to find the vegetarian mains. Then type it in the panel.
2. "Are you open on the 4th of July?" The answer arrives with a booking button. Point out the
   owner's goal doing its work.
3. "Do you have gluten-free pasta?" The agent does not know and says so.
4. The owner's phone buzzes. The agent asks. The owner replies in one line.
5. Ask again. Now it answers, marked verified. No code changed.
6. Switch to Claude. Ask the two-friends question. The restaurant's own component renders in
   Claude. Request a table. The lead appears on the box.
7. Ask Claude for the names of tonight's guests. Nothing. Show the canary test and the blocked
   egress line. Show the overlay: latency, cache hits, cloud calls 0.

**How the build maps to the rubric (as the team understands it)**

| Criterion | What we show |
|---|---|
| Local | All inference, graph, and agents on the box; overlay with zero cloud calls; OpenShell blocking egress; network unplugged for Flow 1 if the venue allows |
| Technical | Constrained selection with code-filled facts; database-enforced partition; fixed retrieval; measured concurrency |
| Business value | Owner goals in every answer; leads captured; the long tail platforms skip; the learning loop |
| Pitch | WIMP to CAC; "it lowers your other CAC"; one live loop from unknown to answered |

**Claims to correct before pitching**

| Do not say | Say instead |
|---|---|
| Shopify will stop merchants pulling their own data in December | Since 1 January 2026 merchants can no longer create an API app from their own Shopify admin; access runs through Shopify's developer platform with 24-hour tokens |
| Restaurants are invisible to AI agents | Platforms have made restaurants orderable inside assistants; the restaurant is a row in their catalog |
| Claude finds our agent from the website | The customer adds the restaurant's connector once |
| It is cheaper than cloud | It is owned, private, and unmetered |
| The box costs about $4,000 | About $6,200 to $9,000 today for 128 GB; $4,999 for the 64 GB model from 23 October |
| ADUI | A2UI (Google's spec), and ours is an A2UI-style catalog |
| AI referrals convert 60% better | True for US retail sites (Adobe, July 2026). Say it is retail data. |

## 15. Build plan

Three workstreams. Times are hours from start; freeze 90 minutes before the deadline.

| Hours | Box and brain | Graph | Surfaces |
|---|---|---|---|
| 0–1 | Confirm NemoClaw, model, and vLLM on the box. Run 30 intents through the selection schema; record validity and latency at 1, 4, 8 concurrent. Start the tunnel. | Postgres up with SCHEMA.md DDL. Seed label registry. | Demo restaurant site (static pages, JSON-LD, one PDF menu). Widget shell with intent box. |
| 1–3 | Intent pipeline end to end with exact cache. Slot extraction. | Ingest the demo site. Embeddings. Retrieval and expansion. Publish. | Six components from surface JSON. Presets. Actions. |
| 3–5 | NemoClaw agents: Gardener on heartbeat, Liaison on Telegram, owner tools. | Binder rules, allergen handling, goal steer. Canary test. Gap storage. | MCP server with `ask_restaurant` text first, then the MCP App. Add connector in Claude. |
| 5–7 | Gap to owner to publish loop working live. Load test. Metrics overlay. | Fixtures from SCHEMA.md section 9. Fix data quality. | History rail, chips, theme. Booking and catering forms to leads. |
| 7–8 | Recovery script. Blocked-egress demo. | Second pass on demo data. | Screen recording of every flow as backup. |
| After | Freeze. Rehearse twice. Submit through BuilderBase. | | |

**Cut lines, in order**

1. MCP App UI not rendering by hour 5: ship text-only `ask_restaurant`, show the component in
   the local MCP Apps test host.
2. Tunnel blocked by venue network: use a phone hotspot; failing that, demo Flow 2 from the
   local test host and say why.
3. Telegram unavailable: use the OpenClaw local dashboard as the owner channel.
4. NemoClaw agents unstable by hour 6: keep one agent doing the gap question only; run
   pre-warming as a plain scheduled job.
5. Structured output unreliable through one backend: switch backend (vLLM or Ollama `format`),
   keep the validator and one retry.

**Check in the first 30 minutes**

- Structured output works with thinking disabled on the installed model.
- The sandboxed agent can reach the owner tools API on the host under the OpenShell policy.
- An outbound tunnel connects from the venue network.
- Whether the demo site carries JSON-LD at item level (most sites do not; seed it if needed).

## 16. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| NemoClaw setup eats hours (alpha; 30–60 min first install; no auto-restart after reboot) | High | One person owns it from minute 0; scripted recovery; minimal agent scope |
| Judges read the direct model path as bypassing the required stack | Medium | Ask a mentor in hour 0; make the agents visibly essential in the demo |
| Cloud assistant in the demo read as "not fully local" | Medium | Frame it as the customer's assistant; all business-side AI is local; have the local host fallback |
| Model picks the wrong component | Medium | Tiny catalog, `use_when` descriptions, intent exemplars, validator, `Answer` fallback |
| Semantic cache returns the wrong answer for near-duplicates (4th vs 5th of July) | Medium | Slots must match exactly; ship exact cache first |
| Live network failure on stage | Medium | Recordings of every flow; Flow 1 works with no internet |
| Wrong allergen information | Low, high impact | Verified-only rendering; fictional demo restaurant; notice component |
| Latency under concurrent load | Medium | Raise sequence limit; short outputs; cache; measure in hour 0 |

## 17. Open questions

**Ask organizers or a mentor now**

1. What is the exact submission deadline in Eastern time?
2. Is there a written rubric? Is there a scoring bonus for smaller teams, as in San Francisco?
3. Must every model call pass through the OpenClaw agent, or may a local service call the same
   local model directly?
4. May a cloud assistant appear in the demo as the external customer's agent?
5. What is preinstalled on the box (NemoClaw, which model weights)?

**Decide as a team**

1. Fictional demo restaurant (recommended, avoids real allergen claims) or a real local one?
2. Owner channel for the demo: Telegram or the local dashboard?
3. Who presents, and who drives the two screens?

## 18. Ideas to build on

- **Demand report.** "Thirty-seven people asked about gluten-free this month and you have no
  tagged items." The intent log is market research the owner has never had.
- **Agent-to-agent negotiation.** The customer's assistant asks for six at 7:00. The local
  agent offers 6:30 or 8:15 and mentions the prix fixe, following the owner's goals.
- **Verified-by-owner as a trust signal.** Assistants prefer sources that state provenance.
  Signed, dated answers are something a scraped page cannot offer.
- **Proposed components.** When a cluster of questions has no fitting element (gift cards,
  private dining), the agent drafts one from primitives and asks the owner to approve it.
- **Same tools in the browser.** Register the tools through WebMCP so browser agents on the
  page use the fixed paths instead of guessing at the DOM.
- **Per-vertical catalogs.** Salon, clinic, repair shop: new components and labels, same core.
- **Voice.** The wireframe has a microphone. Local speech recognition keeps it on the box.

## 19. Glossary

| Term | Meaning |
|---|---|
| Surface | One response: a short sentence plus one to three components with data and actions |
| Selection | The model's output: component names, node ids, parameters |
| Catalog | The owner-approved set of components the model may choose from |
| Binder | Code that validates a selection and fills it with graph data |
| Publish | The step that copies approved public nodes to the serving store |
| Steer | A per-component weight derived from private goals |
| Gap | A question the graph could not answer |
| A2UI | Google's open spec for agent-requested UI from a client-side catalog |
| MCP Apps | The MCP extension that lets a tool return an interactive component; rendered by Claude and ChatGPT |
| A2A | Agent-to-agent protocol (v1.0); used between enterprise agents, not by consumer assistants today |

## 20. Sources

Hackathon and stack

- Event page: https://builderbase.com/event/dell-x-nvidia-ai-hackathon-boston
- Series rules (other cities): https://luma.com/dellxnvdia-hackathon , https://events.cornell.edu/event/dell-x-nvidia-ai-hackathon
- NemoClaw docs: https://docs.nvidia.com/nemoclaw/latest/reference/architecture.html
- NemoClaw on Spark, vLLM defaults: https://docs.nvidia.com/nemoclaw/user-guide/openclaw/inference/local-inference/set-up-vllm
- NVIDIA tutorial (30–90 s, prompt injection note): https://developer.nvidia.com/blog/build-a-secure-always-on-local-ai-agent-with-nvidia-nemoclaw-and-openclaw/
- GB10 throughput: https://rikkarth.com/blog/2026-04-23-benchmark-results-for-qwen-qwen3-6-35b-a3b-fp8-nvidia-dgx-spark-gb10-serving-via-vllm , https://llmrequirements.com/news/2026-06-03-nvfp4-qwen-3-6-35b-dgx-spark
- vLLM structured outputs: https://docs.vllm.ai/en/latest/features/structured_outputs/

Protocols

- Claude web fetch limits: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool
- Custom connectors: https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- MCP Apps quickstart: https://claude.com/docs/connectors/building/mcp-apps/quickstart
- MCP Apps spec: https://modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp
- A2UI: https://a2ui.org/
- A2A: https://a2a-protocol.org/latest/specification/
- A2A card survey: https://apievangelist.com/2026/07/29/most-published-agent-cards-are-not-actually-a2a/

Graph and safety

- pgvector: https://github.com/pgvector/pgvector
- Postgres row security and roles: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- Text-to-Cypher with small models: https://aclanthology.org/2025.emnlp-industry.133.pdf
- schema.org MenuItem: https://schema.org/MenuItem
- FDA allergens: https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/food-allergies
- Massachusetts allergen notice: https://www.law.cornell.edu/regulations/massachusetts/105-CMR-590-011

Generative UI and UX

- Google generative UI paper: https://generativeui.github.io/static/pdfs/paper.pdf
- NN/g on site chatbots: https://www.nngroup.com/articles/site-ai-chatbot/
- NN/g, intent-based interfaces: https://www.nngroup.com/articles/ai-paradigm/

Competition and market

- Square: https://squareup.com/us/en/press/claude-chatgpt-integrations
- Toast in Ask Maps: https://finance.yahoo.com/technology/ai/articles/arriving-now-ai-powered-toast-123000618.html
- ChatGPT bookings: https://www.androidauthority.com/chatgpt-restaurant-reservations-and-waitlists-3696712/
- Owner.com funding and pricing: https://www.prnewswire.com/news-releases/owner-raises-240m-led-by-goldman-sachs-alternatives-to-build-the-ai-native-platform-for-every-local-business-302862420.html , https://www.owner.com/pricing
- NLWeb: https://github.com/nlweb-ai/NLWeb
- Scrunch pricing: https://scrunch.com/pricing
- UCP: https://ucp.dev/
- Amsterdam restaurant study: https://dev.to/blondedevrules/we-built-an-mcp-server-so-any-assistant-can-book-a-table-2le3
- BrightLocal survey: https://www.brightlocal.com/research/local-consumer-review-survey/
- SOCi visibility: https://www.soci.ai/blog/restaurant-local-visibility-benchmarks/
- Adobe AI referral data: https://www.digitalcommerce360.com/2026/08/19/adobe-ai-referral-traffic-data-july-2026/
- Technomic independents: https://www.nrn.com/independent-restaurants/the-independent-restaurant-sector-shrunk-by-2-3-in-2025
- National Restaurant Association forecast: https://restaurant.org/research-and-media/media/press-releases/persistent-cost-increases-and-enduring-demand-will-shape-the-restaurant-industry-in-2026/
- DoorDash commissions: https://merchants.doordash.com/en-us/products/marketplace
- Dell pricing: https://www.dell.com/en-us/shop/desktop-computers/spd/dellpromaxwithgb10fcm1253
- Shopify custom apps change: https://changelog.shopify.com/posts/legacy-custom-apps-can-t-be-created-after-january-1-2026
