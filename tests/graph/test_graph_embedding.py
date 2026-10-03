"""embed(): None without an embedder, else one OpenAI-compatible POST to the local URL."""

from dataclasses import replace

import httpx
from cac_common import embedding
from cac_common.settings import load_settings


def _settings(monkeypatch, base_url: str):
    fake = replace(load_settings({}), embed_base_url=base_url, embed_model="bge-m3")
    monkeypatch.setattr(embedding, "get_settings", lambda: fake)


def test_returns_none_when_embed_base_url_is_empty(monkeypatch):
    _settings(monkeypatch, "")

    def boom(*args, **kwargs):
        raise AssertionError("no request may be made without EMBED_BASE_URL")

    monkeypatch.setattr(embedding.httpx, "post", boom)
    assert embedding.embed(["hello"]) is None


def test_posts_to_embeddings_and_returns_vectors_in_input_order(monkeypatch):
    _settings(monkeypatch, "http://127.0.0.1:9999/v1/")
    seen = {}

    def fake_post(url, *, json, timeout):
        seen.update(url=url, json=json, timeout=timeout)
        data = [{"index": 1, "embedding": [0.3, 0.4]}, {"index": 0, "embedding": [0.1, 0.2]}]
        return httpx.Response(200, json={"data": data}, request=httpx.Request("POST", url))

    monkeypatch.setattr(embedding.httpx, "post", fake_post)
    assert embedding.embed(["a", "b"]) == [[0.1, 0.2], [0.3, 0.4]]
    assert seen["url"] == "http://127.0.0.1:9999/v1/embeddings"
    assert seen["json"] == {"model": "bge-m3", "input": ["a", "b"]}
    assert seen["timeout"] == 10.0
