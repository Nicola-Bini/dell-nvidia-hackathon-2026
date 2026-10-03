"""Static files are looked up on every request; missing builds are 404, traversal is refused."""

from __future__ import annotations

import pytest

from cac_serve.infra import static_files


@pytest.fixture()
def built_repo(tmp_path, monkeypatch):
    widget = tmp_path / "apps" / "widget" / "dist"
    (widget / "assets").mkdir(parents=True)
    (widget / "index.html").write_text("<html>widget</html>", encoding="utf-8")
    (widget / "embed.js").write_text("console.log('embed')", encoding="utf-8")
    (widget / "assets" / "app.js").write_text("console.log('app')", encoding="utf-8")
    site = tmp_path / "apps" / "demo-site" / "dist"
    site.mkdir(parents=True)
    (site / "index.html").write_text("<html>site</html>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("nope", encoding="utf-8")
    monkeypatch.setenv("CAC_REPO_ROOT", str(tmp_path))
    return tmp_path


@pytest.mark.parametrize("path", ["/widget/", "/widget/index.html", "/embed.js", "/site/"])
def test_missing_build_is_404(client, tmp_path, monkeypatch, path):
    monkeypatch.setenv("CAC_REPO_ROOT", str(tmp_path))
    assert client.get(path).status_code == 404


def test_widget_and_site_are_served_once_built(client, built_repo):
    assert "widget" in client.get("/widget/").text
    assert "widget" in client.get("/widget/index.html").text
    assert "app" in client.get("/widget/assets/app.js").text
    assert "embed" in client.get("/embed.js").text
    assert "site" in client.get("/site/").text
    assert client.get("/widget/missing.js").status_code == 404


def test_build_appearing_while_running_is_picked_up(client, tmp_path, monkeypatch):
    monkeypatch.setenv("CAC_REPO_ROOT", str(tmp_path))
    assert client.get("/widget/").status_code == 404
    dist = tmp_path / "apps" / "widget" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html>late</html>", encoding="utf-8")
    assert client.get("/widget/").status_code == 200


@pytest.mark.parametrize(
    "path", ["/widget/%2e%2e/%2e%2e/%2e%2e/secret.txt", "/widget/..%2f..%2f..%2fsecret.txt",
             "/site/%2e%2e/%2e%2e/%2e%2e/secret.txt"],
)
def test_path_traversal_is_refused(client, built_repo, path):
    response = client.get(path)
    assert response.status_code == 404
    assert "nope" not in response.text


def test_resolve_rejects_traversal_and_absolute_paths(built_repo):
    assert static_files.resolve("widget", "../../../secret.txt") is None
    assert static_files.resolve("widget", str(built_repo / "secret.txt")) is None
    assert static_files.resolve("widget", "assets/app.js") is not None
    assert static_files.resolve("widget", "") == (
        built_repo / "apps" / "widget" / "dist" / "index.html"
    ).resolve()
