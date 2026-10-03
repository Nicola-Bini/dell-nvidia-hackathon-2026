# Research: How external assistants can reach the local agent

Gathered 3 October 2026. The fact-check section at the end corrects some claims in the
report; where they differ, the fact-check is the version to use.

## Report

## Bottom line

For Flow 2, build a **remote MCP server with an MCP Apps UI** on the GB10, expose it through a tunnel, and add it to Claude as a **custom connector**. This is the only path today where a mainstream consumer assistant reaches your local agent and renders your own component inline. No consumer assistant speaks A2A to arbitrary sites. The "Claude visits the site and gets redirected to an A2A endpoint" idea does not work in any shipped product.

## (a) What Claude can do with a restaurant URL

- **Web search:** finds indexed pages only. A fresh tunnel URL will not be in any index during the hackathon.
- **Web fetch:** fetches only URLs already in the conversation (user messages, client tool results, prior search/fetch results).
  - It can follow a link it found in a fetched page, but cannot fetch a URL it composed itself (`url_not_in_prior_context`). So `/ask?q=vegetarian` fails unless that exact URL was already seen.
  - URLs max 250 characters; no JavaScript rendering; only text, HTML and PDF; robots.txt is honoured.
  - The model supplies only a URL (no headers or body, per the Claude Desktop third-party doc), so it cannot POST A2A or MCP JSON-RPC.
- **Custom connectors:** remote MCP by URL on Free (one connector), Pro, Max, Team, Enterprise. Claude connects from Anthropic's cloud, never from the user's device, so the box must be publicly reachable over HTTPS.
- **MCP Apps inline:** rendered on Claude web, Desktop, Cowork, iOS and Android. Anthropic states custom connectors use "the exact same runtime" as directory connectors. Purchases through interactive connectors are not supported; a booking form is fine, payment is not.
- **Claude in Chrome** (paid plans) can click through JS-rendered pages. A WebMCP feature request for it was closed as not planned.

## (b) Does any consumer assistant speak A2A to arbitrary websites?

No, from what I found.
- **Gemini Enterprise:** admins can register A2A agents by pasting an agent card. The page I opened labels this Pre-GA and requires A2A v0.3 streaming.
- **Consumer Gemini:** "custom apps" take an MCP server URL (US, 18+, personal account, connect on web).
- **ChatGPT:** adds MCP servers through Developer mode.
- **Claude:** MCP connectors only.
- A2A adoption is enterprise and cloud: Azure AI Foundry, Copilot Studio, Bedrock AgentCore.

## Protocol status

| Protocol | Status I verified |
|---|---|
| A2A | v1.0.0 (GitHub release 2026-03-12; v1.0.1 2026-05-28). Card at `/.well-known/agent-card.json`. JSON-RPC, gRPC and HTTP+JSON bindings. 150+ organisations. Linux Foundation. `a2a-sdk` 1.2.1 on PyPI. |
| MCP | Spec 2026-07-28 (stateless requests). |
| MCP Apps | SEP-1865 Final; spec 2026-01-26. `ui://` resource, MIME `text/html;profile=mcp-app`, tool `_meta.ui.resourceUri`, sandboxed iframe. Hosts: Claude web/Desktop, ChatGPT, VS Code Copilot, Microsoft 365 Copilot, Cursor, Goose, Postman, MCPJam, Archestra, PostHog Code. |
| A2UI | v0.9.1 stable, v1.0 release candidate. Apache-2.0. The client keeps a catalog of pre-approved components and the agent may only request from it. Renderers: Lit, Angular, React, Flutter. Transports: A2A, AG-UI, MCP. An "A2UI in MCP Apps" guide bundles the renderer into a single HTML file. |
| AG-UI | Event-based agent-to-frontend protocol from CopilotKit. MIT. Relevant to Flow 1 only. |
| WebMCP | Chrome 149 origin trial; declarative forms plus imperative `registerTool`. Chrome's own demo is "Le Petit Bistro". |
| NLWeb | MIT. `ask` method plus MCP server, returns schema.org JSON. Last commit 2026-06-10; no releases. |
| llms.txt | A proposal (Jeremy Howard, 2024-09-03). Cheap to add; nothing guarantees assistants read it. |
| schema.org | `Restaurant` has `hasMenu`, `servesCuisine`, `acceptsReservations`, `openingHoursSpecification`. |
| Commerce | ACP (OpenAI and Stripe): Beta, spec 2026-04-17. UCP: v2026-08-25, `/.well-known/ucp`, REST/MCP/A2A/embedded; food vertical "coming soon". AP2: v0.2.0, moving to FIDO. Roadmap slide only. |

NemoClaw is an MCP client only. It "does not launch an MCP server... or listener on the host", so the Flow 2 server must be your own process beside the harness.

## (c) Most reliable 12-hour path

1. **Server:** stateless Streamable HTTP at `POST /mcp`. Anthropic's quickstart is verified with `@modelcontextprotocol/ext-apps@1.7.5` and `@modelcontextprotocol/sdk@1.30.1`. npm latest is ext-apps 2.0.3, which pairs with the v2 split packages; do not mix lines. Python option: `fastmcp[apps]` (4.0.10), whose docs warn of frequent breaking changes in its UI layer.
2. **Tools:** one typed-intent tool (for example `ask_restaurant`) returning `content` text plus `structuredContent` drawn from the public graph only, linked to one `ui://` component. Buttons call `app.callServerTool(...)` for booking, which matches your "clicks are deterministic, no LLM" story.
3. **Tunnel:**
   - ngrok free: one static dev domain, 20,000 requests and 1 GB per month; the interstitial does not affect programmatic traffic.
   - Cloudflare Quick Tunnel: no account, but no SSE support, 200 in-flight requests, no uptime guarantee, random URL. If you use it, set `enableJsonResponse: true`.
   - Named Cloudflare Tunnel: needs an account and a domain on Cloudflare.
   - Tailscale Funnel: ports 443, 8443, 10000 only; `*.ts.net`.
   - Add the tunnel hostname to `allowedHosts`, or `createMcpExpressApp()` returns `403 Invalid Host`.
4. **Connect:** Customize > Connectors > Add, URL ending in `/mcp`. Enable it in the chat and click "Always allow" before the demo.
5. **Gotchas:** call `app.connect()` after registering handlers; give the root non-zero height; keep tool results under about 150,000 characters; list external script origins in `_meta.ui.csp.resourceDomains` or inline everything.

**What to tell judges.** Standard: MCP, the MCP Apps extension (one codebase renders in Claude and ChatGPT), and optionally an A2A v1.0 agent card and schema.org JSON-LD. Bespoke: the knowledge graph, public/private tagging, intent-to-component selection, and discovery. Today the consumer adds the connector once; nobody ships automatic discovery of an agent endpoint from a URL.

## (d) Fallbacks

1. **Claude Desktop, no tunnel:** a stdio entry in `claude_desktop_config.json`; Anthropic's docs suggest `mcp-remote` as a proxy to a remote server. Desktop renders MCP Apps.
2. **`basic-host` from ext-apps:** `SERVERS='["http://<box>:3000/mcp"]' npm run start`, open `http://localhost:8080`. Fully local.
3. **ChatGPT Developer mode** with the same server.
4. **Plain web fetch:** paste the site URL; serve static HTML with the menu and pre-built GET links that return HTML. Text answer only, no component.
5. A screen recording made as soon as the primary path first works.

## Sources opened

- platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool
- claude.com/docs/third-party/claude-desktop/web-tools
- support.claude.com articles 11175166, 13454812, 12012173
- claude.com/docs/connectors/building/testing, /mcp-apps/quickstart, /mcp-apps/getting-started, /mcp-apps/troubleshooting
- modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp, /extensions/client-matrix, /extensions/apps/overview, /specification/latest
- a2a-protocol.org/latest/specification
- linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year
- docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent
- support.google.com/gemini/answer/17209137
- developers.openai.com/apps-sdk/deploy/connect-chatgpt
- a2ui.org, a2ui.org/guides/a2ui-in-mcp-apps, github.com/google/A2UI
- docs.ag-ui.com/introduction
- developer.chrome.com/docs/ai/webmcp, github.com/anthropics/claude-code/issues/30645
- github.com/nlweb-ai/NLWeb, llmstxt.org, schema.org/Restaurant
- github.com/agentic-commerce-protocol/agentic-commerce-protocol, ucp.dev, ap2-protocol.org
- developers.cloudflare.com (Quick Tunnels; create remote tunnel), ngrok.com/docs/pricing-limits/free-plan-limits, tailscale.com/kb/1223/funnel
- docs.nvidia.com/nemoclaw/user-guide/openclaw/manage-sandboxes/mcp-servers/about-managed-mcp-servers
- gofastmcp.com/apps/overview
- github.com/modelcontextprotocol/ext-apps/tree/main/examples/basic-host

## Claims and sources

1. Claude's web fetch tool can only fetch URLs that already appeared in the conversation (user messages, client-side tool results, prior web search or web fetch results). It cannot fetch URLs that appear only in Claude's own output (error url_not_in_prior_context), and URLs are capped at 250 characters. So Claude can follow a link found in a fetched page but cannot compose a new query-string URL. (confidence: high) <https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool>
2. Claude's web fetch does not render JavaScript, supports only text, HTML and PDF content types (unsupported_content_type otherwise), and returns url_not_allowed for robots.txt restrictions and private addresses. (confidence: high) <https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool>
3. Custom connectors (remote MCP) are available on Free (limited to one), Pro, Max, Team and Enterprise. Claude connects to the server from Anthropic's cloud infrastructure, not the user's device, on every client, so the server must be reachable from the public internet. (confidence: high) <https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp>
4. Interactive connectors (MCP Apps) render inline or fullscreen for all users on Claude web, Cowork, Claude Desktop and Claude for iOS/Android. Purchases through third-party interactive connectors are not supported. (confidence: high) <https://support.claude.com/en/articles/13454812-use-interactive-connectors-in-claude>
5. Anthropic states custom connectors use the exact same runtime as directory connectors and recommends exposing a local server through Cloudflare Tunnel or ngrok. With createMcpExpressApp() the tunnel hostname must be added to allowedHosts or requests get 403 Invalid Host. (confidence: high) <https://claude.com/docs/connectors/building/testing>
6. MCP Apps (SEP-1865, created 2025-11-21) has Final status. It defines ui:// resources with MIME type text/html;profile=mcp-app, linked from tools via metadata, rendered in mandatory sandboxed iframes and communicating over MCP JSON-RPC. It unifies MCP-UI and the OpenAI Apps SDK approaches. (confidence: high) <https://modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp>
7. The community-maintained MCP extension matrix lists MCP Apps support in Claude (web), Claude Desktop, VS Code GitHub Copilot, Microsoft 365 Copilot, Goose, Postman, MCPJam, ChatGPT, Cursor, Archestra.AI and PostHog Code. No Gemini client is listed. (confidence: high) <https://modelcontextprotocol.io/extensions/client-matrix>
8. Anthropic's MCP Apps quickstart is verified with @modelcontextprotocol/ext-apps 1.7.5 and @modelcontextprotocol/sdk 1.30.1, using registerAppTool with _meta.ui.resourceUri and registerAppResource. Claude Code does not render the UI; a localhost server must be hosted or tunnelled and added as a custom connector to see it render. (confidence: high) <https://claude.com/docs/connectors/building/mcp-apps/quickstart>
9. Cloudflare Quick Tunnels (cloudflared tunnel --url http://localhost:8080) need no account but do not support Server-Sent Events, cap at 200 in-flight requests (429 beyond), and have no uptime guarantee. (confidence: high) <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/>
10. The ngrok free plan gives one assigned dev domain, up to 3 endpoints, 1 GB data transfer and 20,000 HTTP requests per month. Its browser interstitial does not affect API or programmatic access. (confidence: high) <https://ngrok.com/docs/pricing-limits/free-plan-limits>
11. A2A's latest released spec version is 1.0.0, with Agent Card discovery at https://{server_domain}/.well-known/agent-card.json and three bindings (JSON-RPC, gRPC, HTTP+JSON/REST) exposing operations such as SendMessage and GetTask. (confidence: high) <https://a2a-protocol.org/latest/specification/>
12. A2A agent registration in Google's assistant is an enterprise admin feature: Gemini Enterprise administrators register an agent by supplying agent card JSON. The page marks it Pre-GA and requires the A2A v0.3 streaming mechanism. The consumer Gemini app instead adds custom apps by MCP server URL, so no mainstream consumer assistant was found speaking A2A to arbitrary websites. (confidence: medium) <https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent>
13. A2UI's current production release is v0.9.1 with v1.0 as a release candidate. It is Apache-2.0, and the client keeps a catalog of trusted, pre-approved components that the agent may request from. Renderers include Lit, Angular, React and Flutter, with transports over A2A, AG-UI and MCP. (confidence: high) <https://a2ui.org/>
14. NemoClaw's MCP support makes the sandboxed agent an MCP client of Streamable HTTP servers only. It does not launch an MCP server, bridge, proxy or listener on the host, so an externally facing MCP server must be a separate process. (confidence: high) <https://docs.nvidia.com/nemoclaw/user-guide/openclaw/manage-sandboxes/mcp-servers/about-managed-mcp-servers>

## Recommendations

- Implement Flow 2 as a remote MCP server with one MCP Apps UI resource and present A2A as the roadmap. No consumer assistant will call an A2A endpoint on an arbitrary site today, while Claude and ChatGPT both render MCP Apps.
- Copy Anthropic's quickstart stack exactly: @modelcontextprotocol/ext-apps@1.7.5 with @modelcontextprotocol/sdk@1.30.1, stateless Streamable HTTP at POST /mcp. Do not mix it with the ext-apps 2.x line, which pairs with the v2 split packages. Use fastmcp[apps] only if the team is Python-only, and pin versions.
- Run the MCP server as its own process beside NemoClaw, calling the local LLM and graph over localhost. NemoClaw will not host a listener for you.
- Expose two or three tools at most: one typed-intent tool (for example ask_restaurant) returning text plus structuredContent from public nodes only, and deterministic action tools (for example book_table) that the UI calls through app.callServerTool with no LLM in the loop.
- Enforce the public/private boundary in the MCP tool layer by filtering on the node tag before serialising. Tool calls are proxied through Anthropic's backend, so this is the real external boundary and a concrete privacy talking point.
- Get the tunnel working in the first hour. Prefer ngrok's free static dev domain. If you use a Cloudflare Quick Tunnel, set enableJsonResponse: true because Quick Tunnels do not support SSE. Either way add the tunnel hostname to allowedHosts.
- Keep the tunnel URL stable for the whole event. The connector is registered by URL, so a changed URL means re-adding it.
- Before judging, add the connector under Customize > Connectors, enable it in the demo chat, click 'Always allow', and phrase the prompt to name the connector so Claude does not answer from web search instead.
- Demo a booking or catering-quote form, not payment. Claude does not support purchases through interactive connectors.
- Prepare fallbacks in this order: Claude Desktop with a stdio entry through mcp-remote (no inbound tunnel); the ext-apps basic-host at localhost:8080 pointed at the box (fully local); ChatGPT Developer mode with the same server; a screen recording captured as soon as the primary path works.
- Add cheap discoverability to the restaurant site: visible static HTML for menu, hours and booking; schema.org Restaurant JSON-LD; an llms.txt; and a few pre-built GET links that return HTML answers, so a pasted URL still yields a useful text answer through web fetch.
- Only with two or more hours of slack, add a minimal working A2A v1.0 facade (agent card at /.well-known/agent-card.json plus SendMessage via a2a-sdk 1.2.1) and show it with a scripted client. Do not publish a card that points at nothing.
- Use A2UI's catalog model as the standards anchor for 'owner-approved UI elements' in the pitch. Only bundle an A2UI renderer inside the MCP App if Flow 1 already uses A2UI; otherwise hand-write the HTML component and share the JSON payload shape between flows.
- Tell judges plainly what is standard (MCP, MCP Apps, optional A2A card, schema.org) and what is bespoke (knowledge graph, public/private tagging, intent-to-component selection, discovery). Say that today the consumer adds the connector once and that automatic agent discovery from a URL is not shipped by anyone.

## Open questions

- Is consumer claude.ai web fetch identical to the documented API tool? The URL-provenance, no-JavaScript and content-type rules come from the API docs; I found no consumer-specific page. Test with the real site.
- Does Claude's HTML-to-text conversion keep JSON-LD inside script tags? Not documented, so put key facts and links in visible HTML as well.
- How does Claude's web fetch treat HTTP redirects (same-host and cross-host)? Not documented in the API doc; only the Claude Desktop third-party doc mentions that redirect targets are checked.
- Would a JSON endpoint (application/json, such as an agent card) be fetchable by Claude? The docs say only text, HTML and PDF are supported, which suggests not. Untested.
- Will Claude reliably pick the connector tool over web search for a generic 'restaurants in Cambridge tonight' prompt? Needs live testing; naming the connector in the prompt or switching web search off are the mitigations.
- Which search index backs Claude's web search? Secondary sources say Brave; I did not verify this from an Anthropic primary source.
- Which ChatGPT plans allow Developer mode? The OpenAI help article returned 403; developers.openai.com only says availability depends on account and workspace policies.
- Does the consumer Gemini app render MCP Apps UI from custom apps? Google's help page does not say, and Gemini is absent from the MCP Apps client matrix.
- Is Gemini Enterprise A2A registration GA or Pre-GA? The doc page I opened says Pre-GA; a search snippet of the release notes says GA on 2026-08-17. I did not open the release notes.
- What is the status of MCP server auto-discovery via .well-known server cards (SEP-1649, SEP-2127, SEP-1960)? I saw only secondary sources calling them drafts; not verified.
- Which agents actually call WebMCP tools today? Chrome's docs name none; secondary sources say Gemini in Chrome. The Claude in Chrome request was closed as not planned.
- Does ext-apps 2.0.3 (released 2026-09-25) work with Claude? Anthropic's quickstart is verified only with 1.7.5.
- Is ChatGPT Instant Checkout still live? Secondary sources say it was retired in March 2026; not verified.
- Does the venue network allow outbound tunnel connections (cloudflared, ngrok, Tailscale)? Test in the first hour, with a phone hotspot as backup.
- Does a Cloudflare Quick Tunnel in practice break the MCP SDK's default SSE-framed responses, or only long-lived streams? The docs say SSE is unsupported; untested here.

## Fact-check

1. **confirmed**: 1. Claude's web fetch tool can only fetch URLs that already appeared in the conversation (user messages, client-side tool results, prior web search or web fetch results). It cannot fetch URLs that appear only in Claude's own output (error url_not_in_prior_context), and URLs are capped at 250 characters. So Claude can follow a link found in a fetched page but cannot compose a new query-string URL.
   - Checked against: <https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool>
2. **confirmed**: 2. Claude's web fetch does not render JavaScript, supports only text, HTML and PDF content types (unsupported_content_type otherwise), and returns url_not_allowed for robots.txt restrictions and private addresses.
   - Checked against: <https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool>
3. **confirmed**: 3. Custom connectors (remote MCP) are available on Free (limited to one), Pro, Max, Team and Enterprise. Claude connects to the server from Anthropic's cloud infrastructure, not the user's device, on every client, so the server must be reachable from the public internet.
   - Checked against: <https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp>
4. **confirmed**: 4. Interactive connectors (MCP Apps) render inline or fullscreen for all users on Claude web, Cowork, Claude Desktop and Claude for iOS/Android. Purchases through third-party interactive connectors are not supported.
   - Checked against: <https://support.claude.com/en/articles/13454812-use-interactive-connectors-in-claude>
5. **confirmed**: 5. Anthropic states custom connectors use the exact same runtime as directory connectors and recommends exposing a local server through Cloudflare Tunnel or ngrok. With createMcpExpressApp() the tunnel hostname must be added to allowedHosts or requests get 403 Invalid Host.
   - Checked against: <https://claude.com/docs/connectors/building/testing>
6. **confirmed**: 6. MCP Apps (SEP-1865, created 2025-11-21) has Final status. It defines ui:// resources with MIME type text/html;profile=mcp-app, linked from tools via metadata, rendered in mandatory sandboxed iframes and communicating over MCP JSON-RPC. It unifies MCP-UI and the OpenAI Apps SDK approaches.
   - Checked against: <https://modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp>
7. **confirmed**: 7. The community-maintained MCP extension matrix lists MCP Apps support in Claude (web), Claude Desktop, VS Code GitHub Copilot, Microsoft 365 Copilot, Goose, Postman, MCPJam, ChatGPT, Cursor, Archestra.AI and PostHog Code. No Gemini client is listed.
   - Checked against: <https://modelcontextprotocol.io/extensions/client-matrix>
8. **confirmed**: 8. Anthropic's MCP Apps quickstart is verified with @modelcontextprotocol/ext-apps 1.7.5 and @modelcontextprotocol/sdk 1.30.1, using registerAppTool with _meta.ui.resourceUri and registerAppResource. Claude Code does not render the UI; a localhost server must be hosted or tunnelled and added as a custom connector to see it render.
   - Checked against: <https://claude.com/docs/connectors/building/mcp-apps/quickstart>
9. **confirmed**: 9. Cloudflare Quick Tunnels (cloudflared tunnel --url http://localhost:8080) need no account but do not support Server-Sent Events, cap at 200 in-flight requests (429 beyond), and have no uptime guarantee.
   - Checked against: <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/>
10. **confirmed**: 10. The ngrok free plan gives one assigned dev domain, up to 3 endpoints, 1 GB data transfer and 20,000 HTTP requests per month. Its browser interstitial does not affect API or programmatic access.
   - Checked against: <https://ngrok.com/docs/pricing-limits/free-plan-limits>
11. **corrected**: 11. A2A's latest released spec version is 1.0.0, with Agent Card discovery at https://{server_domain}/.well-known/agent-card.json and three bindings (JSON-RPC, gRPC, HTTP+JSON/REST) exposing operations such as SendMessage and GetTask.
   - Correction: Substance is right, version detail is slightly stale. The spec site still labels 1.0.0 as "Latest Released Version", but the a2aproject/A2A GitHub repo has a newer patch release, v1.0.1 (May 28, 2026; three bug fixes: HTTP binding prefers application/a2a+json, transcoding error changes, TaskStatus values). v1.0.0 was released March 12, 2026. The wire protocol version string is Major.Minor ("1.0", sent in the A2A-Version header), so say "A2A 1.0" in the pitch. Well-known path /.well-known/agent-card.json, the three bindings (JSON-RPC, gRPC, HTTP+JSON/REST) and operations (SendMessage, SendStreamingMessage, GetTask, ListTasks, CancelTask, SubscribeToTask, push-notification config ops, GetExtendedAgentCard) are confirmed.
   - Checked against: <https://github.com/a2aproject/A2A/releases/tag/v1.0.1>
12. **confirmed**: 12. A2A agent registration in Google's assistant is an enterprise admin feature: Gemini Enterprise administrators register an agent by supplying agent card JSON. The page marks it Pre-GA and requires the A2A v0.3 streaming mechanism. The consumer Gemini app instead adds custom apps by MCP server URL, so no mainstream consumer assistant was found speaking A2A to arbitrary websites.
   - Checked against: <https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent>
13. **confirmed**: 13. A2UI's current production release is v0.9.1 with v1.0 as a release candidate. It is Apache-2.0, and the client keeps a catalog of trusted, pre-approved components that the agent may request from. Renderers include Lit, Angular, React and Flutter, with transports over A2A, AG-UI and MCP.
   - Checked against: <https://a2ui.org/reference/renderers/>
14. **confirmed**: 14. NemoClaw's MCP support makes the sandboxed agent an MCP client of Streamable HTTP servers only. It does not launch an MCP server, bridge, proxy or listener on the host, so an externally facing MCP server must be a separate process.
   - Checked against: <https://docs.nvidia.com/nemoclaw/user-guide/openclaw/manage-sandboxes/mcp-servers/about-managed-mcp-servers>

### Found by the fact-checker, missed by the report

All 14 claims re-verified by opening the primary pages; 13 confirmed, 1 corrected (A2A has a v1.0.1 patch release). Caveats and omissions that matter for the spec and the pitch:

FLOW 2 REALITY CHECK (most important)
- Organic discovery will not happen in the demo. Web fetch only takes URLs already in the conversation, and a brand-new tunnel hostname will not be in any search index (the second half is my inference, not a documented statement). "Ask Claude about restaurants in Cambridge" reaches the box only if (a) the custom connector is added and switched on in that chat (+ > Connectors), or (b) the user pastes the URL. Tell judges this plainly. https://claude.com/docs/connectors/building/testing
- The "site redirects Claude to an A2A endpoint" design does not work with any consumer assistant today. The standard path is MCP plus MCP Apps; A2A is enterprise-side only (Gemini Enterprise, Pre-GA, v0.3 streaming with compat packages for 1.0). A static /.well-known/agent-card.json is cheap to serve, but nothing consumer-facing will call it. https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent
- Query-string endpoints: an /ask?q=... URL is fetchable only if that exact URL (250 characters or fewer) appears in a user message or a previously fetched page. Publish pre-composed links in the HTML or llms.txt if you want the paste-a-URL fallback to reach dynamic answers. Fetch results are cached, and the claude.ai search/fetch agent (Claude-User) honors robots.txt. The restriction is documented for the API tool; the consumer help article says the same in looser words. https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool , https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler
- Not verified: whether JSON-LD script blocks survive Claude's HTML-to-text conversion. Put menu, hours and booking facts in visible HTML as well.

CONNECTOR AND MCP APPS DETAILS NOT IN THE CLAIMS
- Connectors are IPv4-only. Claude rejects hostnames resolving to private, loopback or CGNAT (100.64.0.0/10) addresses, so plain Tailscale 100.x addresses fail and only Funnel works. A registered URL that redirects to another host breaks auth; register the final URL. https://claude.com/docs/connectors/building/troubleshooting
- "No sign-in" (authless) connectors are allowed. On Team/Enterprise only an Owner can add a custom connector, so demo from a personal Free/Pro/Max account (Free allows one). https://claude.com/docs/connectors/custom/add-unlisted
- Claude asks permission before the first tool call and UI render (Allow / Always allow); click it before going on stage. On mobile the connector must first be added on web or desktop, and apps render in a native WebView. Display modes are inline card, inline carousel and fullscreen; inline cards have no nested scroll and about two actions. External origins are blocked unless declared in _meta.ui.csp, and frameDomains (third-party iframes) is restricted in Claude, so the MCP App cannot simply iframe the Flow 1 panel. Bundle the HTML. https://claude.com/docs/connectors/building/mcp-apps/design-guidelines
- Purchases are not supported in third-party interactive connectors, so demo a booking request or catering-quote form, not payment.
- Latest MCP spec is 2026-07-28 (stateless requests, per-request capability negotiation). Anthropic's quickstart pins the 1.x SDK line (ext-apps@^1 with sdk 1.x); do not upgrade mid-hackathon. https://modelcontextprotocol.io/specification/latest
- ChatGPT states it "implements the open MCP Apps standard" (developer mode: Settings > Security and login), so the same server is a second demo client. The consumer Gemini app accepts a custom MCP server URL (US, 18+, personal account, Keep Activity on, English, set up on web) but is not in the MCP Apps matrix, so expect text only. https://developers.openai.com/apps-sdk/mcp-apps-in-chatgpt , https://support.google.com/gemini/answer/17209137

TUNNELS
- Quick Tunnel "no SSE" caveat: the MCP TypeScript SDK answers POST /mcp as text/event-stream by default. cloudflared issue #1449 reports POST SSE streams fine and only GET SSE is buffered, so the stateless quickstart server probably works, but it is officially unsupported. De-risk with enableJsonResponse: true on StreamableHTTPServerTransport (it is in the SDK's jsonResponseStreamableHttp example), or use ngrok. https://github.com/cloudflare/cloudflared/issues/1449 , https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/v1.x/src/examples/server/jsonResponseStreamableHttp.ts
- Quick Tunnel hostnames change on every restart, which forces re-adding the connector and updating allowedHosts. ngrok's free static dev domain is stabler as primary (also 4,000 requests/min and 3 agents). The ngrok interstitial is shown to browser HTML traffic, so it would hit human visitors to a Flow 1 site served via ngrok free.
- Tailscale Funnel: all plans; ports 443, 8443, 10000 only; ts.net names only; unpublished bandwidth limits; needs MagicDNS, HTTPS certs and the funnel node attribute. https://tailscale.com/docs/features/tailscale-funnel
- Anthropic's own "MCP tunnels" are Enterprise-only research preview by request; not usable here. https://claude.com/docs/connectors/mcp-tunnels/overview
- Anthropic outbound range for MCP calls is 160.79.104.0/21, usable to lock the tunnel to Claude. https://platform.claude.com/docs/en/api/ip-addresses

FALLBACKS THE RESEARCHER DID NOT LIST
- Claude Desktop renders MCP Apps from local servers configured in claude_desktop_config.json, and Anthropic suggests mcp-remote as a proxy to a remote MCP App. That allows a no-tunnel fallback over the LAN to the GB10; I did not test mcp-remote against a LAN URL. https://claude.com/docs/connectors/building/mcp-apps/getting-started
- MCPJam and Postman are listed as MCP Apps hosts; ChatGPT developer mode is another.

OTHER PROTOCOLS IN THE ASSIGNMENT (not covered by any claim)
- A2UI publishes guides for "A2UI over MCP" and "A2UI in MCP Apps", so "owner-approved A2UI catalog rendered inside an MCP App" is an honest standard-plus-bespoke framing. Jetpack Compose renderer is alpha, SwiftUI planned, and all v1.0 renderers are still planned. https://a2ui.org/reference/renderers/
- WebMCP: Chrome origin trial from Chrome 149; designed for a live tab with a human in the loop, and agents must visit the site to see tools. It fits Flow 1, not Flow 2. Secondary sources say the API moved from navigator.modelContext to document.modelContext in Chrome 150; I could not confirm that on a primary page. https://developer.chrome.com/docs/ai/webmcp
- NLWeb: MIT, self-described proof of concept, /ask plus MCP, returns schema.org JSON. https://github.com/nlweb-ai/NLWeb
- AG-UI: agent-to-frontend event protocol (CopilotKit origin); no consumer assistant acts as an AG-UI client. Relevant to the Flow 1 panel only. https://docs.ag-ui.com/introduction
- llms.txt: informal proposal, no assistant commits to reading it. https://llmstxt.org/
- Commerce: ACP (OpenAI and Stripe, Apache-2.0) powers ChatGPT Instant Checkout and is product-checkout oriented, with no restaurant booking. UCP has Shopping published, Lodging in draft and Food "coming soon"; it works with AP2, A2A and MCP. Neither gives a bookable restaurant flow today. https://www.agenticcommerce.dev/ , https://ucp.dev/

NOT VERIFIED (web search budget ran out)
- Claude's web search provider.
- MCP Server Cards (/.well-known/mcp...) status: secondary sources only, and they conflict. Treat as draft.
- How a host-side MCP server process reaches the NemoClaw-sandboxed agent. The docs apply to NemoClaw v0.0.74 / OpenShell 0.0.116, so prototype this first.
