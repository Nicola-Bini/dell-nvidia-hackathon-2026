"""Entry lookup over kg_public as cac_serve (SCHEMA section 6). Fixed SQL, parameters only.

Two backends for the same question, "which published nodes does this text point at":
cosine similarity over `embedding` when an embedder is configured, and Postgres full-text
search plus pg_trgm over `search_text` when it is not. Neither takes SQL from a caller.
"""

from __future__ import annotations

import re

import psycopg

# Entry nodes are data nodes. A configured form is the one UIComponent that may be an entry.
_ENTRY_NODES = (
    "n.label <> 'BrandTrait'"
    " AND (n.label <> 'UIComponent' OR n.props->>'primitive' = 'FormCard')"
)
_TOKEN = re.compile(r"[a-z0-9]+")
FUZZY_MIN_CHARS = 4
FUZZY_MIN_SIMILARITY = 0.55
# A hit on the node's name outweighs a hit deep in its description or answer.
NAME_HIT, TEXT_HIT, NAME_FUZZY, TEXT_FUZZY = 4.0, 1.0, 3.0, 0.5
# Entries scoring under this share of the best entry are noise next to it.
RELATIVE_CUTOFF = 0.3
# Labels found by name only. The Business node's search_text carries the whole site's nav and
# chip text, and its one-hop expansion is most of the graph.
NAME_ONLY_LABELS = ["Business"]

# Trigram matching is the typo path: it applies only to a token that matches no node by
# full-text search ("guiness"), so a correctly spelt word never drags in look-alikes.
_MISSPELT_SQL = """length(t) >= %(fuzzy_min_chars)s AND NOT EXISTS (
           SELECT 1 FROM kg_public.node n
            WHERE n.business_id = %(business_id)s AND {entry_nodes}
              AND to_tsvector('english', n.search_text) @@ to_tsquery('english', t))"""
_FUZZY_SQL = """
             WHEN tok.misspelt AND strict_word_similarity(tok.t, lower(n.name)) >= %(min_sim)s
               THEN %(name_fuzzy)s * strict_word_similarity(tok.t, lower(n.name))
             WHEN tok.misspelt AND n.label <> ALL(%(name_only)s)
                  AND strict_word_similarity(tok.t, lower(n.search_text)) >= %(min_sim)s
               THEN %(text_fuzzy)s * strict_word_similarity(tok.t, lower(n.search_text))"""

# Coverage first: each query token scores once per node, more for a name hit. ts_rank on the
# whole search_text breaks ties between nodes that cover the same tokens.
_TEXT_SQL = """
WITH tok AS (
  SELECT t, to_tsquery('english', t) AS q, {misspelt} AS misspelt
    FROM unnest(%(tokens)s::text[]) AS t
), scored AS (
  SELECT n.id, length(n.name) AS name_chars,
      ts_rank(to_tsvector('english', n.search_text),
              to_tsquery('english', %(any_token)s), 1) AS rank,
      (SELECT coalesce(sum(CASE
             WHEN to_tsvector('english', n.name) @@ tok.q THEN %(name_hit)s
             WHEN n.label <> ALL(%(name_only)s)
                  AND to_tsvector('english', n.search_text) @@ tok.q THEN %(text_hit)s{fuzzy}
             ELSE 0 END), 0) FROM tok) AS score
    FROM kg_public.node n
   WHERE n.business_id = %(business_id)s AND {entry_nodes}
), ranked AS (
  SELECT id, score, rank, name_chars, max(score) OVER () AS best FROM scored WHERE score > 0
)
SELECT id FROM ranked WHERE score >= %(relative_cutoff)s * best
 ORDER BY score DESC, rank DESC, name_chars, id
 LIMIT %(limit)s
"""

_TEXT_SQL_FUZZY = _TEXT_SQL.format(
    misspelt=_MISSPELT_SQL.format(entry_nodes=_ENTRY_NODES), fuzzy=_FUZZY_SQL,
    entry_nodes=_ENTRY_NODES)
_TEXT_SQL_PLAIN = _TEXT_SQL.format(misspelt="false", fuzzy="", entry_nodes=_ENTRY_NODES)

_VECTOR_SQL = f"""
SELECT n.id
  FROM kg_public.node n
 WHERE n.business_id = %(business_id)s AND {_ENTRY_NODES}
   AND n.embedding IS NOT NULL
   AND 1 - (n.embedding <=> %(vector)s::vector) >= %(threshold)s
 ORDER BY n.embedding <=> %(vector)s::vector, n.id
 LIMIT %(limit)s
"""


def sanitize_tokens(tokens: list[str]) -> list[str]:
    """Keep only [a-z0-9] runs, de-duplicated in order. Safe to join into a tsquery."""
    clean = [part for token in tokens for part in _TOKEN.findall(token.lower())]
    return list(dict.fromkeys(clean))


def has_trigrams(conn: psycopg.Connection) -> bool:
    row = conn.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'").fetchone()
    return row is not None


def text_entries(conn: psycopg.Connection, business_id: str, tokens: list[str],
                 limit: int) -> list[str]:
    """Node ids ranked by full-text matches of the tokens, with trigrams for misspellings."""
    tokens = sanitize_tokens(tokens)
    if not tokens:
        return []
    params = {
        "business_id": business_id, "tokens": tokens, "any_token": " | ".join(tokens),
        "limit": limit, "name_only": NAME_ONLY_LABELS, "relative_cutoff": RELATIVE_CUTOFF,
        "name_hit": NAME_HIT, "text_hit": TEXT_HIT,
    }
    if not has_trigrams(conn):
        return [row[0] for row in conn.execute(_TEXT_SQL_PLAIN, params)]
    params |= {"fuzzy_min_chars": FUZZY_MIN_CHARS, "min_sim": FUZZY_MIN_SIMILARITY,
               "name_fuzzy": NAME_FUZZY, "text_fuzzy": TEXT_FUZZY}
    return [row[0] for row in conn.execute(_TEXT_SQL_FUZZY, params)]


def vector_entries(conn: psycopg.Connection, business_id: str, vector: list[float],
                   limit: int, threshold: float) -> list[str]:
    """Node ids by cosine similarity to the query embedding, weak matches dropped."""
    literal = "[" + ",".join(f"{float(x):.7g}" for x in vector) + "]"
    params = {"business_id": business_id, "vector": literal, "limit": limit,
              "threshold": threshold}
    return [row[0] for row in conn.execute(_VECTOR_SQL, params)]
