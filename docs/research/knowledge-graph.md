# Research: Knowledge graph and retrieval

Gathered 3 October 2026. The fact-check section at the end corrects some claims in the
report; where they differ, the fact-check is the version to use.

## Report

# Knowledge graph and retrieval layer for CAC (one GB10, 12 hours)

## Bottom line
A restaurant graph is a few hundred nodes, so the database matters less than a typed schema, provenance, and where visibility is enforced. Recommended stack: **Postgres + pgvector in one container, typed `node`/`edge` tables, JSON-LD-first ingestion, vector-entry plus fixed-expansion retrieval, and public/private enforced by database role.** Keep the GraphRAG frameworks off the serving path.

## (a) Store status, October 2026
| Option | Status found | Verdict |
|---|---|---|
| Kuzu | Archived 10 Oct 2025 (last 0.11.3). Fork LadybugDB v0.21.2 (1 Oct 2026), MIT, vector + full-text | Kuzu is dead; Ladybug is a viable embedded option |
| Cognee | Defaults are SQLite + LanceDB + Ladybug; Ollama guide uses llama3.1:8b + nomic-embed-text (768d). [One independent test](https://www.glukhov.org/ai-systems/memory/selfhosting-cognee-quickstart-llms-comparison/) saw six 14-30B Ollama models fail structured output | Risky with small models |
| Graphiti 0.30.2 (8 Sep 2026) | Neo4j 5.26 or FalkorDB; Kuzu deprecated; custom Pydantic entity types; warns small models emit schema-invalid JSON; open issue #1947: breaks on FalkorDB 6.0.0 | Only with Neo4j, or FalkorDB pinned to v4.x |
| LightRAG | README: Qwen3-30B-A3B-Instruct is a "reasonable minimum"; default storage is in-memory, small-scale testing only | Heavy for 12 hours |
| Microsoft GraphRAG 3.2.0 | [PyPI](https://pypi.org/project/graphrag/): "largely in maintenance mode"; README warns indexing is expensive | Skip |
| Neo4j Community | Vector indexes in CE, `SEARCH` clause since 2026.01, arm64 image; CE lacks RBAC, property-based access control and multiple databases | Best if you want Cypher and the Browser visual |
| FalkorDB 6.0.0 ([29 Sep 2026](https://www.falkordb.com/blog/announcing-falkordb-6-0/)) | Rust rewrite, SSPLv1, arm64; no 4.x upgrade path until 6.2 | Four days old; never use `:latest` |
| Memgraph 3.13.1 | Vector search; [permission-filtered search](https://memgraph.com/docs/querying/vector-search) is Enterprise | No advantage here |
| Postgres | pgvector 0.8.7: HNSW, `WHERE` filtering, iterative scans; arm64 `pgvector/pgvector:pg18-trixie`. Apache AGE 1.8.0 exists for PG18 but is a second extension you do not need at this size | **Recommended**, without AGE |
| sqlite-vec | Pre-v1 (v0.1.10-alpha.4); [metadata columns and partition keys](https://alexgarcia.xyz/sqlite-vec/features/vec0.html) filter inside KNN | Zero-server fallback |
| LanceDB | Embedded; vector, full-text, SQL filters | Vector only |
| NVIDIA txt2kg | About 30 minutes; ArangoDB + Ollama llama3.1:8b; Qdrant via `--vector-search`; free-form subject-predicate-object triples; README lists GraphRAG as planned. No cuGraph in it; the [CUDA-X playbook](https://build.nvidia.com/spark/cuda-x-data-science) covers only cuDF and cuML | Pitch visual at most |

## (b) Ingestion
- Parse JSON-LD and microdata first with [`extruct`](https://github.com/scrapinghub/extruct). Expect gaps: schema.org reports `Restaurant` on 100K-1M domains but `MenuItem` on only 10K-100K (Google, Aug 2026).
- [Crawl4AI v0.9.4](https://github.com/unclecode/crawl4ai) (23 Sep 2026, Apache-2.0) gives markdown, deep crawl, and LLM extraction through LiteLLM/Ollama. [Firecrawl self-host](https://github.com/firecrawl/firecrawl/blob/main/SELF_HOST.md) needs API, workers, Playwright, Redis, RabbitMQ and Postgres: too heavy.
- PDF and image menus: [Docling](https://github.com/docling-project/docling) runs locally on arm64 with OCR and the GraniteDocling 258M VLM.
- Force schema-valid output: [Ollama `format`](https://docs.ollama.com/capabilities/structured-outputs) takes a JSON schema; [vLLM](https://docs.vllm.ai/en/latest/features/structured_outputs.html) (which the NemoClaw Spark playbook uses) offers `json` and `choice` constraints.
- Small-model extraction is the weak point. The txt2kg README says 70B models give "significantly more accurate" triples; an [NVIDIA blog](https://developer.nvidia.com/blog/insights-techniques-and-evaluation-for-llm-driven-knowledge-graphs/) (Dec 2024) reports 98% triplet accuracy for LoRA-tuned Llama3-8B against 54% for an untuned baseline. Use the largest model that fits for offline ingestion and a small one for serving.
- `FoodEstablishmentReservation` describes actual reservations (confirmations), not availability; model booking as `acceptsReservations` plus your own form. Holiday hours live in `specialOpeningHoursSpecification` and `validFrom`/`validThrough`, so "open July 4th?" should be computed in code.

## (c) Retrieval
Text-to-Cypher is fragile at small sizes. "Mind the Query" (EMNLP 2025) reports zero-shot execution accuracy of 30.99% for Llama-3.1-8B, 26.21% for Granite-3.3-8B, 64.69% for Llama-3.3-70B and 76.75% for the best model; fine-tuned Llama-3.1-8B reaches 70.15%. [PIPE-Cypher](https://arxiv.org/html/2606.08481) (June 2026): Qwen3.5-9B scores 0.963 parse validity but 0.189 execution accuracy. Neo4j's docs say generated Cypher "is not guaranteed to be syntactically correct".

The alternative (Neo4j's VectorCypherRetriever pattern) is vector search for entry nodes, then a fixed, human-written traversal; the LLM never writes a query. I found no head-to-head small-model benchmark, but this removes the measured failure mode.

## (d) Public versus private
[OWASP LLM08:2025](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/) calls for "permission-aware" stores with strict partitioning. [Graphiti](https://help.getzep.com/graphiti/core-concepts/graph-namespacing) itself warns "A namespace filter does not replace application authorization". Postgres row-level security is default-deny, but superusers, table owners and `BYPASSRLS` roles bypass it, so the external agent must connect as a separate non-owner role, not the image's default `postgres`. Strongest: a `kg_public` schema filled only by an owner-approved publish step, with the external role granted nothing else.

## (e) Allergens
FDA lists nine major allergens (sesame added by the FASTER Act, effective 1 Jan 2023). schema.org `MenuItem` has no allergen property, only `suitableForDiet` ([11 `RestrictedDiet` values](https://schema.org/RestrictedDiet), none nut-free). Massachusetts 105 CMR 590 requires the [menu notice](https://concordma.gov/639/Allergy-Awareness-Requirements) "Before placing your order, please inform your server if a person in your party has a food allergy". So allergen and diet edges carry `source`, `verified_by_owner` and `verified_at`; unverified claims render as "not verified, ask staff"; the LLM never writes allergen text.

## (f) Schema outline (proposal)
Common columns: `id, label, props jsonb, visibility, status (draft|approved), source_url, source_type (jsonld|html|pdf|image|owner), verified_by_owner, valid_from, valid_to, embedding`.

- **Public:** Business, Location, HoursSpec, Menu, MenuSection, MenuItem, Offer, Ingredient, Allergen, Diet, AggregateRating, BrandTrait, FAQ, Service (catering, reservations).
- **Private:** Goal, KnowledgeGap, Customer, Booking, Lead.
- **UI:** Intent (example utterances, embedded), UIComponent (catalog id, props schema, approved), Action (deterministic handler).
- **Edges:** HAS_SECTION, HAS_ITEM, HAS_OFFER, CONTAINS, CONTAINS_ALLERGEN{verified}, SUITABLE_FOR{verified}, OPEN_DURING, OFFERS_SERVICE; Intent-RENDERS_WITH->UIComponent; UIComponent-BINDS_TO->label (public only); UIComponent-TRIGGERS->Action; Action-ADVANCES->Goal; KnowledgeGap-ABOUT->Intent.

This maps onto A2UI v0.9: a catalog is a JSON Schema identified by `catalogId`, components bind to a data model by JSON Pointer, and clients advertise `supportedCatalogIds`. Retrieval returns `{componentId, dataModel}`.

## Claims and sources

1. The Kuzu repository was archived on 10 October 2025 and is read-only; 0.11.3 is the last recommended release. The maintained fork is LadybugDB (v0.21.2 released 1 October 2026, MIT, pip install ladybug). (confidence: high) <https://github.com/kuzudb/kuzu>
2. Cognee's default local stores are SQLite (relational), LanceDB (vector) and Ladybug (graph, the renamed Kuzu engine); per-dataset isolation is on by default via ENABLE_BACKEND_ACCESS_CONTROL. (confidence: high) <https://docs.cognee.ai/guides/store-configurations>
3. graphiti-core 0.30.2 was released 8 September 2026; Kuzu support is deprecated because upstream is unmaintained; the docs warn that very small models frequently emit JSON that does not match the requested schema, causing extraction failures. (confidence: high) <https://pypi.org/project/graphiti-core/>
4. Graphiti breaks on FalkorDB 6.0.0 (released 29 September 2026) because db.idx.fulltext.createNodeIndex changed signature in the Rust engine; the issue was open as of filing and the workaround is pinning a v4.x image such as v4.20.7. (confidence: high) <https://github.com/getzep/graphiti/issues/1947>
5. LightRAG's README states Qwen3-30B-A3B-Instruct is a reasonable minimum open-source model for its entity-relation extraction, and that its four default storages are in-memory and intended only for small-scale testing. (confidence: high) <https://github.com/HKUDS/LightRAG>
6. NVIDIA's txt2kg DGX Spark playbook uses ArangoDB (or Neo4j) with Ollama, defaults to llama3.1:8b, serves a web UI on port 3001, and offers Qdrant vector search only via an optional --vector-search flag; it extracts free-form subject-predicate-object triples rather than a typed schema. (confidence: high) <https://build.nvidia.com/spark/txt2kg/instructions>
7. Neo4j Community Edition is GPLv3 and lacks role-based access control, property-based access control, sub-graph access control and multiple databases, so public/private separation cannot be enforced by the database in CE without running separate instances. (confidence: high) <https://neo4j.com/docs/operations-manual/current/introduction/>
8. pgvector's current version is 0.8.7 with HNSW indexes, WHERE-clause filtering and iterative index scans; the pgvector/pgvector:pg18-trixie Docker image is published for arm64 as well as amd64. (confidence: high) <https://github.com/pgvector/pgvector>
9. On the 'Mind the Query' Text2Cypher benchmark (EMNLP 2025 Industry), zero-shot execution accuracy was 30.99% for Llama-3.1-8B-Instruct and 26.21% for Granite-3.3-8B-Instruct versus 64.69% for Llama-3.3-70B and 76.75% for DeepSeek-V3; LoRA fine-tuning lifted Llama-3.1-8B to 70.15%. (confidence: high) <https://aclanthology.org/2025.emnlp-industry.133.pdf>
10. Neo4j's GraphRAG Python docs state that the LLM-generated query in Text2CypherRetriever is not guaranteed to be syntactically correct, while VectorCypherRetriever runs a vector index search and then a fixed developer-written retrieval query to traverse from the matched nodes. (confidence: high) <https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html>
11. PostgreSQL row-level security is default-deny when enabled with no policy, but superusers, roles with BYPASSRLS and (unless FORCE ROW LEVEL SECURITY is set) table owners bypass it. (confidence: high) <https://www.postgresql.org/docs/current/ddl-rowsecurity.html>
12. schema.org MenuItem has only four type-specific properties (menuAddOn, nutrition, offers, suitableForDiet), has no allergen property, and is used on 10K-100K domains (Google, August 2026) compared with 100K-1M domains for Restaurant. (confidence: high) <https://schema.org/MenuItem>
13. FDA recognises nine major food allergens (milk, eggs, fish, Crustacean shellfish, tree nuts, peanuts, wheat, soybeans, sesame); sesame was added by the FASTER Act signed 23 April 2021, effective 1 January 2023. (confidence: high) <https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/food-allergies>
14. A2UI v0.9 defines available UI components in a JSON Schema catalog identified by catalogId, binds components to a data model using JSON Pointers, and has clients advertise supportedCatalogIds; messages are createSurface, updateComponents, updateDataModel and deleteSurface. (confidence: high) <https://a2ui.org/specification/v0.9-a2ui/>

## Recommendations

- Use one Postgres container (pgvector/pgvector:pg18-trixie, arm64) as graph plus vector store: a node table, an edge table and an HNSW index on node.embedding. At a few hundred nodes, 1-2 hop expansion is plain SQL joins; do not add Apache AGE, Cognee, Graphiti, LightRAG or Microsoft GraphRAG to the serving path.
- Enforce public/private in the database, not the prompt: create a non-superuser, non-owner role for the visitor-facing and A2A agents that can read only a kg_public schema (or RLS policy visibility='public' AND status='approved'). Never let those agents connect as the image's default postgres superuser, which bypasses RLS. Promote rows to public only through an owner-approval publish step.
- Seed a canary private node (for example a fake customer name) and write one automated test that the A2A endpoint and the iframe endpoint cannot retrieve it under adversarial prompts. Show that test in the pitch for the 'local' and 'technical' criteria.
- Ingest in this order: extruct for JSON-LD/microdata, Crawl4AI markdown for pages, Docling for PDF and image menus, then LLM extraction into Pydantic models with JSON-schema-constrained decoding (Ollama format or vLLM structured outputs). Stamp every node with source_url, source_type and extracted_by.
- Use the largest model that fits in the 128 GB box for offline ingestion and graph improvement, and a small fast model for serving. Ingestion is latency-insensitive; published evidence says triple quality rises sharply with model size or fine-tuning.
- Do not use text-to-Cypher or text-to-SQL with the small serving model. Embed the typed intent, take top-k public nodes plus Intent nodes, run a fixed expansion template per label, then have the LLM choose a component id from an enumerated candidate list (constrained 'choice' output) and fill slots.
- Answer hours, holiday and price questions in code from HoursSpec and Offer nodes; the LLM only routes the intent. Cache on normalised intent to (component id, node ids) so repeat questions skip the LLM, which also eases the concurrency worry.
- Treat allergens and diet claims as verified edges only: CONTAINS_ALLERGEN and SUITABLE_FOR carry verified_by_owner and verified_at. If unverified, render a fixed 'not verified, please ask staff' component with the Massachusetts notice text; never let the LLM generate allergen-free statements.
- Hand-seed about six UIComponent nodes (MenuList, ItemCard with add-to-cart, HoursCard, BookingForm, CateringQuoteForm, FallbackContact) and about fifteen Intent nodes with example utterances, linked by RENDERS_WITH, BINDS_TO and ADVANCES edges to Goal nodes. Shape them as an A2UI v0.9 catalog so retrieval returns {componentId, dataModel}.
- Have the graph-improver sub-agent write only status='draft' nodes and KnowledgeGap nodes (unanswered intents); the owner dashboard flips status to approved. This gives the 'proposes new UI elements and reports gaps' story with no extra infrastructure.
- If the team wants Cypher and a graph visual, the fallback is Neo4j Community in two separate containers (public and private), since CE has no RBAC. If using FalkorDB, pin a v4.x tag; 6.0.0 shipped on 29 September 2026 and already breaks Graphiti.
- Treat NVIDIA txt2kg as an optional pitch visual only if time remains. It produces untyped triples in ArangoDB and cannot bind to owner-approved components.

## Open questions

- I found no head-to-head benchmark of vector-entry plus fixed expansion versus text-to-Cypher with models under about 10B parameters. The recommendation rests on measured text-to-Cypher failure rates and on removing query generation entirely.
- Does the demo restaurant's site carry JSON-LD at all, and at MenuItem level? Run extruct against it in the first hour; schema.org usage figures suggest item-level markup is uncommon.
- Which model does the hackathon box's NemoClaw install select for vLLM, and does the OpenShell network policy let the sandboxed agent reach a local Postgres port? Not verified.
- I could not confirm cuGraph aarch64/CUDA 13 wheels for DGX Spark (the PyPI page failed to load). It is irrelevant at this graph size but should not be claimed in the pitch.
- The mass.gov primary page for the allergen regulation returned 403; the notice wording was confirmed on a municipal page (Concord, MA). Whether the notice legally applies to an online ordering panel was not determined.
- The NVIDIA 2024 blog's 54% baseline was labelled inconsistently by the page reader (an untuned larger model, possibly Llama2-70B); check the figure before quoting it.
- Exact release dates for Apache AGE 1.7.0/1.8.0 could not be read reliably; only the version numbers and PG18 support are confirmed.
- No embedding model was benchmarked on the GB10. Cognee's guide uses nomic-embed-text at 768 dimensions as one known-working local option; retrieval quality on short menu text is untested.
- FalkorDB per-graph ACLs (restricting a user to one graph key) could not be verified; the docs page returned 404.

## Fact-check

1. **confirmed**: 1. Kuzu repo archived 10 Oct 2025, read-only; 0.11.3 is the last release; maintained fork is LadybugDB (v0.21.2, 1 Oct 2026, MIT, pip install ladybug).
   - Checked against: <https://github.com/kuzudb/kuzu>
2. **confirmed**: 2. Cognee default local stores are SQLite (relational), LanceDB (vector), Ladybug (graph, renamed Kuzu); per-dataset isolation is on by default via ENABLE_BACKEND_ACCESS_CONTROL.
   - Checked against: <https://docs.cognee.ai/guides/store-configurations>
3. **confirmed**: 3. graphiti-core 0.30.2 released 8 Sep 2026; Kuzu support deprecated because upstream is unmaintained; docs warn very small models frequently emit JSON that does not match the schema, causing extraction failures.
   - Checked against: <https://pypi.org/project/graphiti-core/>
4. **confirmed**: 4. Graphiti breaks on FalkorDB 6.0.0 (released 29 Sep 2026) because db.idx.fulltext.createNodeIndex changed signature in the Rust engine; issue open; workaround is pinning a v4.x image such as v4.20.7.
   - Checked against: <https://github.com/getzep/graphiti/issues/1947>
5. **confirmed**: 5. LightRAG README: Qwen3-30B-A3B-Instruct is a reasonable minimum local model for entity-relation extraction; the four default storages are in-memory and intended only for small-scale testing.
   - Checked against: <https://github.com/HKUDS/LightRAG>
6. **confirmed**: 6. NVIDIA txt2kg DGX Spark playbook uses ArangoDB (or Neo4j) with Ollama, defaults to llama3.1:8b, web UI on port 3001, Qdrant vector search only via optional --vector-search; extracts free-form subject-predicate-object triples, not a typed schema.
   - Checked against: <https://build.nvidia.com/spark/txt2kg/instructions>
7. **confirmed**: 7. Neo4j Community Edition is GPLv3 and lacks role-based, property-based and sub-graph access control and multiple databases, so public/private separation cannot be DB-enforced in CE without separate instances.
   - Checked against: <https://neo4j.com/docs/operations-manual/current/introduction/>
8. **confirmed**: 8. pgvector current version is 0.8.7 with HNSW, WHERE-clause filtering and iterative index scans; pgvector/pgvector:pg18-trixie image is published for arm64 and amd64.
   - Checked against: <https://github.com/pgvector/pgvector>
9. **confirmed**: 9. 'Mind the Query' Text2Cypher benchmark (EMNLP 2025 Industry): zero-shot execution accuracy 30.99% Llama-3.1-8B-Instruct, 26.21% Granite-3.3-8B-Instruct, 64.69% Llama-3.3-70B, 76.75% DeepSeek-V3; LoRA fine-tuning lifted Llama-3.1-8B to 70.15%.
   - Checked against: <https://aclanthology.org/2025.emnlp-industry.133.pdf>
10. **confirmed**: 10. Neo4j GraphRAG Python docs: Text2CypherRetriever's LLM-generated query is not guaranteed to be syntactically correct; VectorCypherRetriever does a vector index search then a developer-written retrieval query to traverse from matched nodes.
   - Checked against: <https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html>
11. **confirmed**: 11. PostgreSQL RLS is default-deny when enabled with no policy; superusers, BYPASSRLS roles and (unless FORCE ROW LEVEL SECURITY) table owners bypass it.
   - Checked against: <https://www.postgresql.org/docs/current/ddl-rowsecurity.html>
12. **confirmed**: 12. schema.org MenuItem has only four type-specific properties (menuAddOn, nutrition, offers, suitableForDiet), no allergen property, used on 10K-100K domains (Google, August 2026) vs 100K-1M for Restaurant.
   - Checked against: <https://schema.org/MenuItem>
13. **confirmed**: 13. FDA recognises nine major food allergens (milk, eggs, fish, Crustacean shellfish, tree nuts, peanuts, wheat, soybeans, sesame); sesame added by FASTER Act signed 23 April 2021, effective 1 January 2023.
   - Checked against: <https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/food-allergies>
14. **confirmed**: 14. A2UI v0.9 defines components in a JSON Schema catalog identified by catalogId, binds via JSON Pointers, clients advertise supportedCatalogIds; messages are createSurface, updateComponents, updateDataModel, deleteSurface.
   - Checked against: <https://a2ui.org/specification/v0.9-a2ui/>

### Found by the fact-checker, missed by the report

All 14 claims held up against primary sources (GitHub/PyPI/Docker Hub APIs, raw READMEs, the paper PDF, vendor docs) checked on 2026-10-03. The web-search budget ran out mid-task, so the items below come from direct fetches only; I could not look for head-to-head studies of vector-then-expand versus text-to-Cypher.

**Pitfalls that affect the build**
- **FalkorDB `latest` is still broken for Graphiti.** Docker `falkordb/falkordb:latest` now points to 6.0.1 (1 Oct 2026), which only rebuilt dependencies. Graphiti's README quickstart still says to run `:latest`, so following it today fails. The newest 4.x is v4.22.0 (30 Sep), not v4.20.7. https://github.com/FalkorDB/FalkorDB/releases , https://github.com/getzep/graphiti
- **Ladybug/Kuzu allows one read-write process.** You can have one READ_WRITE Database object with many connections, or several READ_ONLY processes, but not both. The three sub-agents cannot each open the same embedded file if one writes; they need a single API process in front. Cognee's default graph store inherits this. https://docs.ladybugdb.com/concurrency/
- **Cognee defaults to OpenAI for both LLM and embeddings.** If only the LLM is switched, embeddings still go to api.openai.com, which breaks the "fully local" criterion. Set both `LLM_*` and `EMBEDDING_*` blocks. Current version is 1.6.2 (29 Sep 2026); its docs also warn that small models return malformed JSON. https://docs.cognee.ai/guides/store-configurations , https://docs.cognee.ai/setup-configuration/llm-providers
- **Postgres RLS is silently bypassed by the Docker default user.** `POSTGRES_USER` in the official image (which pgvector's image builds on) is a superuser. The external-agent service must connect as a separate non-owner, non-superuser role. https://github.com/docker-library/docs/blob/master/postgres/content.md
- **txt2kg repo and NVIDIA page disagree.** The build.nvidia.com page lists `--neo4j` (Neo4j + Ollama) and `--vllm` (Neo4j + vLLM with Llama-3.3-Nemotron-Super-49B FP8, first start 30+ minutes). The `start.sh` on GitHub main today exposes only `--dev-frontend`, `--vllm` and `--vector-search`. Run `./start.sh --help` on the box. The txt2kg README does not mention cuGraph and lists vector KNN GraphRAG as a future enhancement. https://github.com/NVIDIA/dgx-spark-playbooks/tree/main/nvidia/txt2kg

**Options the claims did not cover**
- **Apache AGE now has row-level security.** RLS support landed in 1.7.0 (Jan-Feb 2026), and arm64 images exist (`release_PG18_1.8.0`). Postgres + AGE + pgvector + RLS is therefore a single store with database-enforced public/private separation. https://github.com/apache/age/releases
- **Neo4j CE includes vector and full-text indexes**, so VectorCypherRetriever works on CE; arm64 community images exist (5.26.31). https://neo4j.com/docs/operations-manual/current/introduction/
- **Current versions (GitHub/PyPI, today):** Microsoft GraphRAG 3.2.0 (Sep 2026), LightRAG 1.5.7, neo4j-graphrag 1.22.0 (1 Oct), Memgraph 3.13.1, LanceDB 0.39.0, sqlite-vec 0.1.9 (Mar 2026, still pre-1.0, last push May 2026), Crawl4AI 0.9.4 (Apache-2.0), Firecrawl AGPL-3.0 (last tagged release v2.11.0, June 2026), extruct 0.18.0 for JSON-LD.

**Nuances for the pitch**
- **Text2Cypher evidence is weaker than claim 9 suggests.** The same table shows few-shot lifts Llama-3.1-8B to 46.05% and Granite-8B to 38.83%, and Phi-4 (14B) reaches 62.01% zero-shot. The paper does not compare against vector-entry plus fixed traversal, so it shows 8B text-to-Cypher is unreliable, not that the alternative is better. https://aclanthology.org/2025.emnlp-industry.133.pdf
- **A2UI v0.9 is the previous stable version.** v0.9.1 is the current production release and v1.0 is a release candidate (adds `actionResponse`, renames theme to surfaceProperties). Cite v0.9.1. https://a2ui.org/

**Schema.org gaps for the demo questions**
- **"Open July 4th?"** needs `specialOpeningHoursSpecification` (on Place) with `validFrom`/`validThrough`; a spec with no `opens` means closed. https://schema.org/OpeningHoursSpecification
- **RestrictedDiet has 11 values only** (Diabetic, GlutenFree, Halal, Hindu, Kosher, LowCalorie, LowFat, LowLactose, LowSalt, Vegan, Vegetarian). There is no nut-free or dairy-free, so allergens need a custom node type. https://schema.org/RestrictedDiet
- **FoodEstablishmentReservation describes confirmed reservations**, not bookability; use it for the booking result. https://schema.org/FoodEstablishmentReservation

**Allergen legal anchors**
- The FDA page says FALCPA labeling does not apply to food wrapped after a customer's order (made-to-order restaurant food), and that FDA has set no threshold for any allergen. So "allergen-free" cannot be asserted from ingredient lists alone. https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/food-allergies
- Massachusetts 105 CMR 590.011(C)(2) (under M.G.L. c.140 s.6B) requires menus and menu boards to carry a notice asking customers to tell their server about any food allergy before ordering. That is a ready-made mandatory disclaimer component for a Boston restaurant demo. https://www.law.cornell.edu/regulations/massachusetts/105-CMR-590-011 , https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXX/Chapter140/Section6B
