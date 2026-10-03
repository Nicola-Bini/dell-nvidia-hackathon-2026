"""The owner's inbox as one self-contained HTML page. Every value goes through `esc`: lead
payloads and the agent's reasons are data, never markup."""

import json
from html import escape
from typing import Any

STYLE = """
:root{color-scheme:light dark;--bg:#fafaf7;--fg:#1c1b19;--mut:#6b675f;--line:#ddd8cd;
--card:#fff;--ok:#1f7a45;--bad:#a8321f;--ac:#7a4e12}
@media(prefers-color-scheme:dark){:root{--bg:#171613;--fg:#ecebe6;--mut:#a29d92;--line:#37342d;
--card:#201f1b;--ok:#5ec489;--bad:#ef8a76;--ac:#e0b062}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}
main{max-width:980px;margin:0 auto;padding:16px}
h1{font-size:22px;margin:8px 0 2px}h2{font-size:16px;margin:28px 0 8px;color:var(--ac)}
.sub{color:var(--mut);margin:0 0 8px}.empty{color:var(--mut);font-style:italic}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;
margin:8px 0}.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.grow{flex:1;min-width:220px}.tag{font-size:12px;border:1px solid var(--line);border-radius:99px;
padding:1px 8px;color:var(--mut)}code,pre{font:12px/1.4 ui-monospace,monospace;white-space:pre-wrap;
word-break:break-word;background:transparent;margin:4px 0}
button{font:inherit;padding:5px 12px;border-radius:6px;border:1px solid var(--line);
background:var(--card);color:var(--fg);cursor:pointer}button.go{border-color:var(--ok);
color:var(--ok)}button.no{border-color:var(--bad);color:var(--bad)}
button:disabled{opacity:.5;cursor:wait}.why{margin:4px 0}.ev{color:var(--mut);font-size:13px}
"""

SCRIPT = """
document.addEventListener('click', async (e) => {
  const b = e.target.closest('button[data-act]'); if (!b) return;
  const act = b.dataset.act, id = b.dataset.id; let url, body = null;
  if (act === 'verify-edge') { url = '/owner/verify'; body = {edge_ids: [Number(id)]}; }
  else { url = '/owner/changes/' + id + '/' + act;
    if (act === 'reject') { const r = prompt('Why? (the agent will see this)', '');
      if (r === null) return; body = {reason: r}; } }
  b.disabled = true;
  const res = await fetch(url, {method: 'POST', credentials: 'same-origin',
    headers: {'Content-Type': 'application/json', 'X-Requested-With': 'cac-inbox'},
    body: body ? JSON.stringify(body) : null});
  if (res.ok) location.reload(); else { b.disabled = false;
    alert('Could not do that: ' + (await res.text()).slice(0, 200)); }
});
"""


def esc(value: Any) -> str:
    return escape("" if value is None else str(value))


def compact(value: Any) -> str:
    return esc(json.dumps(value, ensure_ascii=False, default=str, separators=(", ", ": ")))


def _evidence(evidence: dict) -> str:
    if not evidence:
        return ""
    parts = [f"{esc(k)}: {esc(v)}" for k, v in evidence.items()]
    return f'<div class="ev">Evidence: {"; ".join(parts)}</div>'


def _change(c: dict, buttons: str) -> str:
    diff = ""
    if c.get("before") is not None:
        diff += f"<pre>was: {compact(c['before'])}</pre>"
    diff += f"<pre>{'wants' if c['state'] == 'pending' else 'set'}: {compact(c['after'])}</pre>"
    return (f'<div class="card"><div class="row"><div class="grow">'
            f'<strong>{esc(c["action"])}</strong> <code>{esc(c["target"])}</code> '
            f'<span class="tag">{esc(c["tier"])}</span> '
            f'<span class="tag">#{esc(c["change_id"])}</span>'
            f'<div class="why">{esc(c["reason"])}</div>{_evidence(c["evidence"])}{diff}</div>'
            f'<div class="row">{buttons}</div></div></div>')


def _button(act: str, cid: Any, label: str, cls: str = "") -> str:
    return (f'<button class="{cls}" data-act="{esc(act)}" data-id="{esc(cid)}">'
            f'{esc(label)}</button>')


def _section(title: str, sub: str, items: list[str]) -> str:
    body = "".join(items) or '<p class="empty">Nothing here.</p>'
    return (f'<section><h2>{esc(title)} ({len(items)})</h2>'
            f'<p class="sub">{esc(sub)}</p>{body}</section>')


def _tag(t: dict) -> str:
    who = "agent" if t["source_type"] == "agent" else t["source_type"]
    line = (f'<strong>{esc(t["src_name"])}</strong> {esc(t["type"])} '
            f'<strong>{esc(t["dst_name"])}</strong> <span class="tag">{esc(who)}</span> '
            f'<span class="tag">shown as "not verified"</span>')
    return (f'<div class="card"><div class="row"><div class="grow">{line}</div>'
            f'{_button("verify-edge", t["edge_id"], "Confirm", "go")}</div></div>')


def _lead(lead: dict) -> str:
    return (f'<div class="card"><strong>{esc(lead["kind"])}</strong> '
            f'<span class="tag">{esc(lead["component"])}</span> '
            f'<span class="tag">{esc(lead["channel"])}</span> '
            f'<span class="ev">{esc(lead["ts"])}</span><pre>{compact(lead["payload"])}</pre></div>')


def _gap(g: dict) -> str:
    return (f'<div class="card"><strong>{esc(g["topic"])}</strong> '
            f'<span class="tag">{esc(g["count"])} asked</span> '
            f'<span class="tag">{esc(g["state"])}</span></div>')


def render(data: dict) -> str:
    pending = [_change(c, _button("approve", c["change_id"], "Approve", "go")
                       + _button("reject", c["change_id"], "Reject", "no"))
               for c in data["pending"]]
    applied = [_change(c, _button("revert", c["change_id"], "Revert", "no"))
               for c in data["applied"]]
    sections = [
        _section("Pending changes",
                 "The agent proposed these. Nothing is public until you approve.", pending),
        _section("Unverified tags", "Shown to visitors as \"not verified, ask staff\" until you "
                 "confirm.", [_tag(t) for t in data["unverified_tags"]]),
        _section("Applied changes", "Live now. Revert puts the old version back.", applied),
        _section("New leads", "Requests from visitors. Details stay on this box.",
                 [_lead(x) for x in data["leads"]]),
        _section("Open gaps", "Questions visitors asked that have no confirmed answer.",
                 [_gap(g) for g in data["gaps"]]),
    ]
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Owner inbox</title><style>{STYLE}</style></head><body><main>'
            f'<h1>Owner inbox</h1><p class="sub">What your agent changed, and what needs your '
            f'say.</p>{"".join(sections)}</main><script>{SCRIPT}</script></body></html>')
