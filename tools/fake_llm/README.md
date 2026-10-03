# fake_llm

An OpenAI-compatible stand-in for the local model, for laptops (OWNERSHIP seam 6). No model
and no network: selections come from the keyword rules in `rules.py`. The box runs the real
model; nothing here ships to it.

```bash
uv run tools/fake_llm/server.py --port 8000        # LLM_BASE_URL=http://127.0.0.1:8000/v1
uv run --with pytest --with jsonschema pytest tools/fake_llm -q
```

| Endpoint | Returns |
|---|---|
| `GET /v1/models` | `{ "object": "list", "data": [{ "id": "fake-llm", "object": "model" }] }` |
| `POST /v1/chat/completions` | A chat completion whose `choices[0].message.content` is the Selection as compact JSON |
| `GET /stats` | `{ "calls": n }`: chat completions served since start or the last reset |
| `POST /reset` | Sets the call count to zero |

The request is the one the Serve API sends (SCHEMA 8.1): the schema is read from
`response_format.json_schema.schema`, and the last message must be

```
<data>
<id> | <label> | <name> | <facts>
</data>
Visitor: <the visitor's text>
```

The selection always validates against the schema it was given and uses only components and
ids that schema offers; a pick that does not validate becomes `{"kind":"off_topic"}`.

Rule order (`rules.py`, first match wins): allergen, catering, booking, configured forms,
hours, an FAQ sharing two or more content words, a named menu item, a diet, an FAQ sharing one
specific word, a menu section, generic cards, then gap or off topic. It is deterministic and
knows nothing about meaning, so it is for wiring and tests, not for judging answer quality.
