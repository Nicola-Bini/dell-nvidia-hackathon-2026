"""The Serve API refuses to start unless the model and embedder hosts are local."""

from __future__ import annotations

import pytest
from cac_common.settings import load_settings

from cac_serve.infra.startup_checks import assert_local
from cac_serve.main import create_app


def test_startup_fails_with_a_cloud_model_host():
    settings = load_settings({"LLM_BASE_URL": "https://api.example.com/v1"})
    with pytest.raises(RuntimeError, match="LLM_BASE_URL"):
        create_app(settings)


def test_startup_fails_with_a_cloud_embedder_host():
    settings = load_settings({"EMBED_BASE_URL": "https://api.example.com/v1"})
    with pytest.raises(RuntimeError, match="EMBED_BASE_URL"):
        create_app(settings)


def test_startup_succeeds_with_a_loopback_model_host():
    settings = load_settings({"LLM_BASE_URL": "http://127.0.0.1:8000/v1", "EMBED_BASE_URL": ""})
    assert create_app(settings).title


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1:8000/v1", "http://localhost:8000/v1", "http://127.9.9.9/v1",
     "http://[::1]:8000/v1"],
)
def test_loopback_hosts_pass(url):
    assert_local(url, "LLM_BASE_URL")


def test_own_address_passes():
    assert_local(
        "http://box.lan:8000/v1", "LLM_BASE_URL",
        resolve=lambda host: ["192.168.1.20"], is_own=lambda addr: addr == "192.168.1.20",
    )


def test_foreign_address_fails_and_names_the_variable():
    with pytest.raises(RuntimeError, match="EMBED_BASE_URL"):
        assert_local(
            "http://10.0.0.9:8000/v1", "EMBED_BASE_URL",
            resolve=lambda host: [host], is_own=lambda addr: False,
        )


def test_mixed_resolution_fails():
    with pytest.raises(RuntimeError, match="LLM_BASE_URL"):
        assert_local(
            "http://sneaky.example:8000/v1", "LLM_BASE_URL",
            resolve=lambda host: ["127.0.0.1", "203.0.113.7"], is_own=lambda addr: False,
        )


def test_unresolvable_host_fails():
    def boom(host):
        raise OSError("no such host")

    with pytest.raises(RuntimeError, match="LLM_BASE_URL"):
        assert_local("http://nowhere.invalid/v1", "LLM_BASE_URL", resolve=boom)


@pytest.mark.parametrize("url", ["", "not a url", "http:///v1"])
def test_url_without_a_host_fails(url):
    with pytest.raises(RuntimeError, match="LLM_BASE_URL"):
        assert_local(url, "LLM_BASE_URL")
