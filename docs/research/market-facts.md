# Research: Market and business facts

Gathered 3 October 2026. The fact-check section at the end corrects some claims in the
report; where they differ, the fact-check is the version to use.

## Report

## CAC market facts (checked 2026-10-03)

**Headline corrections:** the Shopify claim is wrong as worded, and a cloud API is cheaper than the box for serving 3,000 visitors. The cost case only holds for always-on background agents.

### 1. Restaurant market and current costs
- **Size.** NRA forecasts $1.55T in 2026 sales across "more than 1 million" outlets; 42% of operators were unprofitable last year ([NRA](https://restaurant.org/research-and-media/media/press-releases/persistent-cost-increases-and-enduring-demand-will-shape-the-restaurant-industry-in-2026/)). Datassential counts ~859,000 active restaurants ([Jan 2026](https://datassential.com/resource/foodservice-industry-trends-2026/)).
- **Independents.** Technomic counts 412,498 at end-2025, down 2.3% ([NRN](https://www.nrn.com/independent-restaurants/the-independent-restaurant-sector-shrunk-by-2-3-in-2025)). 7 in 10 restaurants are single-unit ([NRA](https://restaurant.org/research-and-media/research/industry-statistics/national-statistics/)). Massachusetts has 15,294 locations ([NRA fact sheet](https://restaurant.org/research-and-media/research/industry-statistics/massachusetts-state-fact-sheet/)).
- **Websites.** 83% of US small businesses have one; 41% use Wix/Squarespace-type builders ([Clutch, Aug 2025](https://clutch.co/press-releases/smb-websites-2025)).
- **Tech appetite.** 60% of operators plan customer-facing tech investment; 26% use AI, 6% for customer orders ([Restaurant Dive](https://www.restaurantdive.com/news/national-restaurant-assocation-operator-artificial-intelligence-adoption/812418/)).

| Vendor | What restaurants pay | Source |
|---|---|---|
| Owner.com | $249/mo + 5% per order, or $499/mo flat; 5% guest fee on both | [official](https://www.owner.com/pricing) |
| DoorDash | 15% / 25% / 30% delivery, 6% pickup | [official](https://merchants.doordash.com/en-us/products/marketplace) |
| OpenTable | $149–$499/mo plus $1.00–$1.50 per network cover | [secondary](https://restaurant.eatapp.co/blog/opentable-pricing) |
| Popmenu | $179 / $299 / $499 per month; ordering add-on ~$50 | [secondary](https://orderitto.com/compare/popmenu-pricing) |
| Toast | online ordering ~$75/mo on a $69/mo POS plan | [secondary](https://www.getsauce.com/post/toast-online-ordering-pricing-fees) |
| BentoBox | now sold only to Clover POS customers | [official](https://www.getbento.com/pricing/) |

### 2. Pitch-ready statistics
1. 45% of US consumers used ChatGPT or similar for local recommendations in 2026, up from 6% in 2025 ([BrightLocal, n=1,002](https://www.brightlocal.com/research/local-consumer-review-survey/)).
2. Restaurant brands appear in Google's local 3-pack 24.3% of the time; ChatGPT recommends them 5.3% ([SOCi](https://www.soci.ai/blog/restaurant-local-visibility-benchmarks/); multi-location brands, not independents).
3. AI-referred visits to US retail sites convert 60% better and earn 53% more per visit; traffic is up 62% year over year ([Adobe, July 2026](https://www.digitalcommerce360.com/2026/08/19/adobe-ai-referral-traffic-data-july-2026/); retail, not restaurants).
4. Traffic from AI agents and agentic browsers grew 7,851% in 2025 ([HUMAN Security via Benton](https://www.benton.org/headlines/2026-state-ai-traffic-cyberthreat-benchmark-report)).
5. None of the major AI crawlers render JavaScript ([Vercel/MERJ, Dec 2024](https://vercel.com/blog/the-rise-of-the-ai-crawler)); about 39% of retailer homepages are not machine-readable (Adobe, same link as 3).
6. Diners reached through AI tools spend 20% more ([OpenTable via PYMNTS](https://www.pymnts.com/news/artificial-intelligence/2026/opentable-reports-diners-reached-through-ai-tools-spend-20percent-more/)); 44% of Americans planned to use AI more to find and book restaurants ([OpenTable, n=1,527](https://www.prnewswire.com/news-releases/opentable-reveals-the-top-trends-set-to-define-dining-in-2026-302618592.html)).
7. Amazon shoppers who use Rufus are 60% more likely to buy ([Modern Retail](https://www.modernretail.co/technology/amazon-says-its-ai-shopping-assistant-is-gaining-traction-with-rufus-users-up-115/)).
8. Vendor-reported: +35.2% conversion for TFG with Bloomreach's agent ([Bloomreach](https://www.bloomreach.com/en/products/loomi-conversational-agent)); 12.3% vs 3.1% conversion for chat-engaged shoppers ([Rep AI via Algolia](https://www.algolia.com/blog/ecommerce/conversational-ai-in-ecommerce)). Both carry self-selection bias.

### 3. Shopify claim, corrected
- Oct 30, 2025: from Jan 1, 2026, new custom apps can no longer be created in the Shopify admin. Existing ones keep working; new ones go through the Dev Dashboard ([changelog](https://changelog.shopify.com/posts/legacy-custom-apps-can-t-be-created-after-january-1-2026)).
- Dev Dashboard apps reach a merchant's own store via client credentials: same organization only, tokens expire in 24 hours ([docs](https://shopify.dev/docs/apps/build/authentication-authorization/client-credentials-grant)).
- REST Admin API has been legacy since Oct 1, 2024 ([docs](https://shopify.dev/docs/api/admin-rest)).
- Feb 27, 2026: partner and API terms bar training AI on merchant or customer data without written consent ([FAQ](https://help.shopify.com/en/partners/help-support/faq/ppa)).
- Sept 28, 2026: Shopify opened checkout to browser AI agents ([TechCrunch](https://techcrunch.com/2026/09/28/shopify-opens-checkout-to-browser-based-ai-agents/)).
- I found nothing dated December that stops merchants exporting their own data.

**Accurate version:** "Since January 1, 2026, Shopify merchants can no longer create an API app from their own admin. Access to their own data now runs through Shopify's developer platform, 24-hour tokens, and terms that restrict AI use of that data."

### 4. Hardware economics

| Item | Figure | Source |
|---|---|---|
| Dell Pro Max with GB10, 128GB/4TB | $9,007 today; 1TB option is −$2,830 (≈$6,177) | [Dell](https://www.dell.com/en-us/shop/desktop-computers/spd/dellpromaxwithgb10fcm1253) |
| Same box, 1TB, March 2026 | $4,061 | [StorageReview](https://www.storagereview.com/review/dell-pro-max-with-gb10-review) |
| DGX Spark 64GB | $4,999, on sale Oct 23 | [PC Enthusiast](https://thepcenthusiast.com/nvidia-dgx-spark-64gb-price-release-date/) |
| DGX Spark 128GB | $6,950 reported, not NVIDIA-confirmed | [shattered.io](https://shattered.io/nvidia-dgx-spark-64gb-vs-128gb-pricing-2026/) |
| Power | 40–45W idle, 60–90W LLM inference, under 200W peak | [ServeTheHome](https://www.servethehome.com/nvidia-dgx-spark-review-the-gb10-machine-is-so-freaking-cool/4/) |
| Electricity | 24.41¢/kWh, Massachusetts commercial | [EIA](https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_5_6_a) |

My estimates from those inputs:
- **Running cost.** 60W average is about 44 kWh, or $11/month. Hardware amortized over 36 months is $172–$250/month.
- **Managed price.** A 12–18-month hardware payback ([Hardfin](https://blog.hardfin.com/developing-hardware-as-a-service-haas-pricing-plans)) implies $343–$515/month, inside the Owner.com/Popmenu band.
- **Cloud comparison.** 3,000 intents/month at 3,000 input and 300 output tokens costs about $13.50 on Claude Haiku 4.5 ($1/$5 per MTok) or $27 on Sonnet 5.5 ([pricing](https://platform.claude.com/docs/en/about-claude/pricing)).
- **Where the box wins.** A background agent emitting 30 tokens/s around the clock produces ~78M output tokens/month, about $390 on Haiku 4.5 before input tokens.
- **Concurrency.** StorageReview measured a 20B model at ~91 tok/s, rising to ~1,585 tok/s under batching (my reading of its range). NVIDIA says Nemotron 3 Super 120B takes 30–90 seconds per response on this hardware ([NVIDIA](https://developer.nvidia.com/blog/build-a-secure-always-on-local-ai-agent-with-nvidia-nemoclaw-and-openclaw/)).

### 5. Privacy and regulation
- **Sentiment.** 51% of small-business decision-makers cite data privacy as an AI concern; food service has the lowest AI adoption ([Homebase, n=750](https://www.joinhomebase.com/blog/small-business-ai-gap-report)). 37% of restaurant operators not using AI cite privacy ([Restaurant365](https://www.restaurant365.com/guides/2026-state-of-the-restaurant-industry-mid-year-report/)).
- **California.** Chat-widget suits allege the third-party vendor eavesdrops; damages are $5,000 per violation ([NatLawReview](https://natlawreview.com/article/protecting-against-invasion-privacy-chat-box-class-actions)). Small businesses faced 4,000+ claims in four years ([CalMatters](https://calmatters.org/economy/technology/2026/09/california-privacy-act-reform-for-small-business-helped-big-tech/)).
- **States.** 20 have comprehensive privacy laws; 35,000–100,000-consumer thresholds exempt most single restaurants ([Consenteo](https://www.consenteo.com/knowledge-hub/legal/us_state_privacy_law_tracker_2026)).
- **Massachusetts.** 201 CMR 17.00 requires a written security program and vendor vetting from any business holding a resident's name plus SSN, licence or card number ([TrustArc](https://trustarc.com/regulations/massachusetts-sppi/)). Comprehensive bills are in conference, effective 2027 ([Foley Hoag](https://foleyhoag.com/news-and-insights/blogs/state-ag-insights/2026/june/one-step-closer-to-a-massachusetts-data-privacy-law-comparing-the-current-house-and-senate-bills/)).

### 6. TAM / SAM / SOM (at $399/month, my assumption)
- **TAM:** 859,000 restaurants × $4,788/yr ≈ $4.1B.
- **SAM:** 412,498 independents × 83% with a website ≈ 342,000 ≈ $1.6B.
- **SOM:** Massachusetts, 15,294 × 70% single-unit × 83% ≈ 8,900; 3% in two years ≈ 267 boxes ≈ $1.3M ARR.

### Not sourced
- Share of restaurant sites with PDF or image menus: no figure found.
- Restaurant tech spend as a share of revenue: not found.
- OpenTable, Popmenu and Toast prices are from secondary pages; the official ones blocked me.
- The "36.2M US small businesses" figure appeared only in search results; SBA pages returned 403.

## Claims and sources

1. Shopify announced on Oct 30, 2025 that from Jan 1, 2026 new custom apps can no longer be created in the Shopify admin; existing custom apps keep working and new ones must be built in the Dev Dashboard. It does not stop merchants reading their own data, and nothing is dated December. (confidence: high) <https://changelog.shopify.com/posts/legacy-custom-apps-can-t-be-created-after-january-1-2026>
2. California chat-widget privacy suits carry a mandatory $5,000 penalty per violation; small businesses faced 4,000+ claims in four years, and SB 690 (passed by the legislature in Sept 2026) moves pen-register enforcement to the attorney general. (confidence: medium) <https://calmatters.org/economy/technology/2026/09/california-privacy-act-reform-for-small-business-helped-big-tech/>
3. 45% of US consumers used ChatGPT or other generative AI for local business recommendations in 2026, up from 6% in 2025, making it the third most-used source after Google and Facebook (n=1,002, published Feb 11, 2026). (confidence: high) <https://www.brightlocal.com/research/local-consumer-review-survey/>
4. The average restaurant brand appears in Google's local 3-pack 24.3% of the time but is recommended by ChatGPT 5.3%, Gemini 7.1% and Perplexity 7.6% of the time (SOCi 2026 Local Visibility Index; multi-location brands, not independents). (confidence: medium) <https://www.soci.ai/blog/restaurant-local-visibility-benchmarks/>
5. In July 2026, AI-referred visits to US retail sites converted 60% better than non-AI traffic, earned 53% more revenue per visit, and grew 62% year over year (1,219% since Oct 2024); about 39% of analyzed retailer homepages were not machine-readable. This is retail data, not restaurant data. (confidence: high) <https://www.digitalcommerce360.com/2026/08/19/adobe-ai-referral-traffic-data-july-2026/>
6. Traffic from AI agents and agentic browsers grew 7,851% year over year in 2025, and AI-driven traffic overall grew 187% from January to December 2025 (HUMAN Security 2026 report, read via a third-party summary because the primary page returned 403). (confidence: medium) <https://www.benton.org/headlines/2026-state-ai-traffic-cyberthreat-benchmark-report>
7. None of the major AI crawlers (GPTBot, ClaudeBot, PerplexityBot) render JavaScript, so client-side-rendered content such as a JS-injected panel is invisible to them (Vercel/MERJ, Dec 17, 2024; may have changed since). (confidence: medium) <https://vercel.com/blog/the-rise-of-the-ai-crawler>
8. There were 412,498 independent restaurants in the US at the end of 2025, down 2.3% (more than 9,500 locations) from 2024, per preliminary Technomic data. (confidence: high) <https://www.nrn.com/independent-restaurants/the-independent-restaurant-sector-shrunk-by-2-3-in-2025>
9. The National Restaurant Association forecasts $1.55 trillion in 2026 restaurant and foodservice sales across more than 1 million outlets, and 42% of operators reported being unprofitable in the prior year. (confidence: high) <https://restaurant.org/research-and-media/media/press-releases/persistent-cost-increases-and-enduring-demand-will-shape-the-restaurant-industry-in-2026/>
10. Owner.com charges restaurants $249/month plus 5% per order, or $499/month flat, with a 5% guest-paid order fee on both plans; month-to-month, includes website, online ordering, app and loyalty. (confidence: high) <https://www.owner.com/pricing>
11. DoorDash Marketplace charges restaurants 15% (Basic), 25% (Plus) or 30% (Premier) commission on delivery orders and 6% on pickup, with no monthly fee. (confidence: high) <https://merchants.doordash.com/en-us/products/marketplace>
12. Dell lists the Dell Pro Max with GB10 (128GB, 4TB) at $9,007.00 as of Oct 3, 2026, with a 1TB option at −$2,830 (about $6,177) and a 280W USB-C adapter. The same 1TB box was $4,061 in March 2026, so pricing is volatile. (confidence: high) <https://www.dell.com/en-us/shop/desktop-computers/spd/dellpromaxwithgb10fcm1253>
13. NVIDIA's NemoClaw tutorial for DGX Spark features Nemotron 3 Super 120B and states inference with it typically takes 30–90 seconds per response on that hardware, which is too slow for a live website intent box. (confidence: high) <https://developer.nvidia.com/blog/build-a-secure-always-on-local-ai-agent-with-nvidia-nemoclaw-and-openclaw/>
14. Claude Haiku 4.5 costs $1 per million input tokens and $5 per million output tokens (Sonnet 5.5: $2/$10), so 3,000 intents a month at 3,000 input and 300 output tokens each costs roughly $13.50–$27 on a cloud API. The token volumes are my assumption. (confidence: medium) <https://platform.claude.com/docs/en/about-claude/pricing>

## Recommendations

- Replace the Shopify line in the pitch with the accurate version: since Jan 1, 2026 merchants can no longer create an API app from their own Shopify admin; access to their own data runs through the Dev Dashboard, 24-hour tokens and terms that restrict AI use. A judge who knows Shopify will catch the current wording.
- Do not pitch the box as cheaper than cloud for serving visitors: a cloud API handles 3,000 intents a month for under $30. Pitch flat cost for always-on background agents (a continuous sub-agent costs hundreds of dollars a month in cloud tokens), data that never leaves the premises, and no per-order commission.
- Price it as a managed appliance at $299–$499/month and anchor against Owner.com ($499 flat), OpenTable ($149–$499 plus $1.00–$1.50 per cover) and DoorDash (15–30%). A 12–18-month hardware payback on a ~$6,177 box supports $343–$515.
- Use a small, fast model for the live intent path and keep the 120B Nemotron model for the background graph-improvement agent. NVIDIA's own tutorial quotes 30–90 seconds per response for the 120B model on this hardware; a 20B-class model measured about 91 tokens/s on the Dell box.
- Answer the concurrency worry with numbers: 3,000 visitors a month is a few LLM calls per hour, and the Dell box batches a 20B model to roughly 1,585 tokens/s in StorageReview's test (my reading of its range). Add caching and deterministic click paths as planned.
- Expose Flow 2 as server-rendered content (plain HTML or JSON plus the A2A endpoint), not only inside the JavaScript iframe. The Vercel/MERJ study found AI crawlers do not execute JavaScript, so an iframe-only panel would be invisible to them.
- Open the pitch with three numbers: 45% of consumers now ask AI for local recommendations (up from 6%), ChatGPT recommends restaurant brands 5.3% of the time versus 24.3% in Google's 3-pack, and AI-referred visits convert 60% better. Say aloud that the last one is retail data.
- On the privacy slide, say chat logs and reservation data stay on the owner's box with no third-party chat vendor, which is the party California chat-widget suits target at $5,000 per violation. Keep card numbers, SSNs and licence numbers out of the graph entirely so Massachusetts 201 CMR 17.00 is not triggered by the agent.
- Show the SOM as a Massachusetts beachhead (about 8,900 single-unit restaurants with websites; 3% is roughly 267 boxes and $1.3M ARR) rather than leading with the $4.1B TAM.
- Quote hardware prices with today's date: Dell lists $9,007 for 128GB/4TB, and the 64GB DGX Spark starts at $4,999 from Oct 23. Prices have more than doubled since March, so a judge may have a different number in mind.

## Open questions

- No quantified source found for the share of restaurant websites that publish menus as PDFs or images; Yext only says they are hard for AI to process.
- Restaurant tech spend as a percentage of revenue was not found; the Hospitality Technology 2026 study page returned 403. Only directional data is sourced (60% plan customer-facing tech investment, 26% use AI).
- OpenTable, Popmenu and Toast prices come from secondary comparison sites because the official pricing pages timed out or returned 403; verify before putting them on a slide.
- The $6,950 price for the 128GB DGX Spark is reported by outlets on Oct 2, 2026 but not confirmed by NVIDIA; I could not open NVIDIA's marketplace page (timeout).
- The '36.2 million US small businesses' figure (SBA Office of Advocacy) appeared only in search results; both SBA pages returned 403, so it is not verified and is not used in the TAM.
- The 83% small-business website share is all industries (Clutch); I found no restaurant-specific website-ownership figure, so the SAM uses it as a proxy.
- No public restaurant-specific data on AI-referral conversion exists beyond OpenTable's '20% more spend'; the Adobe conversion numbers are retail e-commerce.
- SOCi's visibility gap covers multi-location brands; independents' AI visibility is not measured. The '83% of restaurants invisible on ChatGPT' and '22% of diners use AI to choose restaurants' figures seen in blogs were not traced to a primary source and are not used.
- The Texas and Nebraska privacy laws have no volume threshold per the tracker I read; whether their small-business carve-outs exempt a single restaurant was not checked.
- Scripts and checkout.liquid sunset dates were only partly verified: Shopify's help page confirms Aug 26, 2026 for Thank-you/Order-status pages; the June 30, 2026 Scripts end date is from secondary sources.
- Which configuration of the Dell box is the prize and the demo unit (128GB vs 64GB, storage size) is unknown; it changes both the price quoted and which models fit.
- The cloud-versus-local comparison rests on my assumed token volumes (3,000 input / 300 output per intent; 30 tokens/s for a continuous agent); measure real numbers from the build before quoting them.
- The judging split (25% each for pitch, local, business value, technical) was not verified against any event page.

## Fact-check

1. **confirmed**: 1. Shopify announced on Oct 30, 2025 that from Jan 1, 2026 new custom apps can no longer be created in the Shopify admin; existing custom apps keep working and new ones must be built in the Dev Dashboard. It does not stop merchants reading their own data, and nothing is dated December.
   - Checked against: <https://changelog.shopify.com/posts/legacy-custom-apps-can-t-be-created-after-january-1-2026>
2. **corrected**: 2. California chat-widget privacy suits carry a mandatory $5,000 penalty per violation; small businesses faced 4,000+ claims in four years, and SB 690 (passed by the legislature in Sept 2026) moves pen-register enforcement to the attorney general.
   - Correction: SB 690 is now law. The Senate concurred 39-0 on Aug 28, 2026 (not September); the Governor signed it on Sept 30, 2026 (Chapter 976, Statutes of 2026). It has no urgency clause, so it should take effect Jan 1, 2027 (my inference from the standard rule, not stated in the bill). It only amends Penal Code 637.2 so that pen-register/trap-and-trace claims (Section 638.51) arising from websites or apps can be brought only by the Attorney General, retroactive to pending actions commenced within two years before the operative date. It does not touch Section 631 wiretap claims, which are the usual basis for chat-widget suits, so private chat-transcript suits remain possible. The $5,000 is statutory damages per violation (or three times actual damages); 'mandatory' is CalMatters' wording. The 4,000+ figure is an estimate from defence attorneys about claims over cookies and analytics trackers, not chat widgets.
   - Checked against: <https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260SB690>
3. **confirmed**: 3. 45% of US consumers used ChatGPT or other generative AI for local business recommendations in 2026, up from 6% in 2025, making it the third most-used source after Google and Facebook (n=1,002, published Feb 11, 2026).
   - Checked against: <https://www.brightlocal.com/research/local-consumer-review-survey/>
4. **confirmed**: 4. The average restaurant brand appears in Google's local 3-pack 24.3% of the time but is recommended by ChatGPT 5.3%, Gemini 7.1% and Perplexity 7.6% of the time (SOCi 2026 Local Visibility Index; multi-location brands, not independents).
   - Checked against: <https://www.soci.ai/blog/restaurant-local-visibility-benchmarks/>
5. **confirmed**: 5. In July 2026, AI-referred visits to US retail sites converted 60% better than non-AI traffic, earned 53% more revenue per visit, and grew 62% year over year (1,219% since Oct 2024); about 39% of analyzed retailer homepages were not machine-readable. This is retail data, not restaurant data.
   - Checked against: <https://www.digitalcommerce360.com/2026/08/19/adobe-ai-referral-traffic-data-july-2026/>
6. **confirmed**: 6. Traffic from AI agents and agentic browsers grew 7,851% year over year in 2025, and AI-driven traffic overall grew 187% from January to December 2025 (HUMAN Security 2026 report, read via a third-party summary because the primary page returned 403).
   - Checked against: <https://www.globenewswire.com/news-release/2026/04/09/3270682/0/en/human-security-s-2026-state-of-ai-traffic-cyberthreat-benchmark-report-signals-a-new-internet-era-automation-growth-now-outpaces-humans.html>
7. **confirmed**: 7. None of the major AI crawlers (GPTBot, ClaudeBot, PerplexityBot) render JavaScript, so client-side-rendered content such as a JS-injected panel is invisible to them (Vercel/MERJ, Dec 17, 2024; may have changed since).
   - Checked against: <https://vercel.com/blog/the-rise-of-the-ai-crawler>
8. **confirmed**: 8. There were 412,498 independent restaurants in the US at the end of 2025, down 2.3% (more than 9,500 locations) from 2024, per preliminary Technomic data.
   - Checked against: <https://www.nrn.com/independent-restaurants/the-independent-restaurant-sector-shrunk-by-2-3-in-2025>
9. **confirmed**: 9. The National Restaurant Association forecasts $1.55 trillion in 2026 restaurant and foodservice sales across more than 1 million outlets, and 42% of operators reported being unprofitable in the prior year.
   - Checked against: <https://restaurant.org/research-and-media/media/press-releases/persistent-cost-increases-and-enduring-demand-will-shape-the-restaurant-industry-in-2026/>
10. **confirmed**: 10. Owner.com charges restaurants $249/month plus 5% per order, or $499/month flat, with a 5% guest-paid order fee on both plans; month-to-month, includes website, online ordering, app and loyalty.
   - Checked against: <https://www.owner.com/pricing>
11. **confirmed**: 11. DoorDash Marketplace charges restaurants 15% (Basic), 25% (Plus) or 30% (Premier) commission on delivery orders and 6% on pickup, with no monthly fee.
   - Checked against: <https://merchants.doordash.com/en-us/products/marketplace>
12. **confirmed**: 12. Dell lists the Dell Pro Max with GB10 (128GB, 4TB) at $9,007.00 as of Oct 3, 2026, with a 1TB option at -$2,830 (about $6,177) and a 280W USB-C adapter. The same 1TB box was $4,061 in March 2026, so pricing is volatile.
   - Checked against: <https://www.dell.com/en-us/shop/desktop-computers/spd/dellpromaxwithgb10fcm1253>
13. **confirmed**: 13. NVIDIA's NemoClaw tutorial for DGX Spark features Nemotron 3 Super 120B and states inference with it typically takes 30-90 seconds per response on that hardware, which is too slow for a live website intent box.
   - Checked against: <https://developer.nvidia.com/blog/build-a-secure-always-on-local-ai-agent-with-nvidia-nemoclaw-and-openclaw/>
14. **confirmed**: 14. Claude Haiku 4.5 costs $1 per million input tokens and $5 per million output tokens (Sonnet 5.5: $2/$10), so 3,000 intents a month at 3,000 input and 300 output tokens each costs roughly $13.50-$27 on a cloud API. The token volumes are my assumption.
   - Checked against: <https://platform.claude.com/docs/en/about-claude/pricing>

### Found by the fact-checker, missed by the report

Thirteen of 14 claims hold; claim 2 needed correcting. My web search budget ran out early, so the gaps listed at the end are unverified, not checked and found empty.

**Hardware pricing changed yesterday (affects claim 12 and the business case)**
- On Oct 2, 2026 NVIDIA introduced a 64GB DGX Spark at $4,999 with half the RAM and storage; a 64GB Dell Pro Max with GB10 is also $4,999, available Oct 23. https://hothardware.com/news/nvidia-dgx-spark-64gb-release
- The 128GB DGX Spark rose to about $6,950 (The Register) or $6,995 (HotHardware), up from $4,699. The Register calls that nearly 75% above launch price. https://www.theregister.com/Tag/DGX%20Spark/
- NVIDIA's product page lists no price, shows the 64GB model as "coming soon", and gives a 240W power supply and 140W GB10 TDP. https://www.nvidia.com/en-us/products/workstations/dgx-spark/
- The March 2026 price in claim 12 is $4,061.34 for the 1TB configuration, per StorageReview on Mar 3, 2026. https://www.storagereview.com/review/dell-pro-max-with-gb10-review

**Cost comparison cuts against "cheaper than cloud"**
- Power: Dell ships a 280W adapter; StorageReview saw about 70W GPU power peak in one test. No source gives a whole-system average.
- My own arithmetic, not sourced: at an assumed 100W average, 24/7 is about 72 kWh a month, roughly $12-$22 at $0.17-$0.30 per kWh.
- That is about the same as the $13.50-$27 cloud API cost in claim 14, before $5k-$9k of hardware. The pitch should rest on privacy, ownership and no per-token metering, not on cost savings.
- Claim 14 caveat: the pricing page says Claude 4.7 and later models use a tokenizer producing about 30% more tokens for the same text, so the Sonnet 5.5 figure is nearer $35 for identical text. Prompt caching would lower it.

**Concurrency worry**
- The 30-90 second figure in claim 13 applies only to the 120B model; "too slow for a live intent box" is the researcher's inference, though a reasonable one.
- StorageReview's vLLM tests on the same box show batched throughput of about 2,776 tok/s for Llama 3.1 8B and 4,453 tok/s for GPT-OSS-20B at batch size 64. A small model with batching can plausibly serve many concurrent visitors. https://www.storagereview.com/review/dell-pro-max-with-gb10-review

**Shopify (assignment item 3)**
- Shopify's help centre still says a custom app can "access your store's data directly using Shopify's APIs". https://help.shopify.com/en/manual/apps/app-types/custom-apps
- The only December-dated item I found is unrelated: unpublished apps could not be created as of Dec 9, 2019. https://help.shopify.com/en/partners/help-support/faq/unpublished-app-deprecation
- The 2026 developer changelog shows script tags stopping on March 1, 2027 and API version 2027-01 removals, nothing restricting merchants' own data. https://shopify.dev/changelog
- I could not check REST Admin API deprecation, the checkout.liquid sunset or agentic storefront terms. The team should drop the "December" claim.

**Caveats on confirmed claims**
- Claim 7: the same Vercel study says Gemini (via Googlebot) and AppleBot do render JavaScript. It is from Dec 2024 and covers crawlers; I could not find newer data. For Flow 2, serve server-rendered HTML or structured data plus the A2A endpoint; do not rely on the iframe panel.
- Claim 5: verified through Digital Commerce 360; I did not open Adobe's own publication.
- Claim 6: the primary press release is dated Apr 9, 2026; the Benton summary says March.
- Claim 3: BrightLocal puts Google first at 71%; the Facebook percentage was not in the text I retrieved.

**Assignment items with no claim and no source (do not use in the pitch unsourced)**
- Share of small businesses with websites.
- Restaurant tech spend.
- Popmenu, BentoBox and Toast pricing (Popmenu and Toast pages returned 403).
- OpenTable cover fees (page timed out).
- Conversion lift from conversational or intent-based on-site search (item 4).
- Hardware-as-a-service or managed pricing benchmarks.
- TAM/SAM/SOM sketch. Only the top-line inputs are verified: 412,498 independents, more than 1 million outlets, $1.55 trillion in sales.
- Privacy regulation beyond California's CIPA, including anything Massachusetts-specific for a Boston audience.
