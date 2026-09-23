"""Suggested stores: only ones not already watched, and only checked ones."""
import pytest
from fastapi.testclient import TestClient

from monitor import db, suggestions


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    db.init_db()
    monkeypatch.setattr("monitor.config.API_KEY", "k")
    monkeypatch.setattr("monitor.main.API_KEY", "k")
    from monitor.main import app
    with TestClient(app) as c:
        c.headers.update({"Authorization": "Bearer k"})
        yield c


def names(client):
    return [s["name"] for s in client.get("/api/suggestions").json()["stores"]]


def test_a_store_you_already_watch_is_not_suggested(client, monkeypatch):
    monkeypatch.setattr("monitor.routes.suggestions.STORES", [
        {"name": "Mohawk", "url": "https://mohawkgeneralstore.com/collections/all"},
        {"name": "Oi Polloi", "url": "https://www.oipolloi.com/collections/all"},
    ])
    assert names(client) == ["Mohawk", "Oi Polloi"]

    # Any part of the store counts, and www. or not makes no difference.
    db.create_watch(name="oi", brand="oipolloi.com", strategy="shopify",
                    kind="collection", url="https://oipolloi.com/collections/sale")

    assert names(client) == ["Mohawk"]


def test_it_needs_auth(client):
    client.headers.pop("Authorization")
    assert client.get("/api/suggestions").status_code in (401, 503)


def test_every_shipped_suggestion_was_checked_and_is_watchable():
    """A suggestion that cannot be watched is worse than none."""
    for s in suggestions.STORES:
        assert s["url"].startswith("https://") and "/collections/" in s["url"], s
        assert s.get("checked"), f"{s['name']} was never checked"
        assert s.get("products", 0) > 0, s["name"]
        if s.get("sale_url"):
            assert s["sale_url"].startswith("https://"), s


def test_a_watch_from_a_suggestion_keeps_its_brand_filter(client):
    """What the dashboard sends when Start watching is pressed."""
    r = client.post("/api/watches", json={
        "url": "https://shopneighbour.com/collections/all", "strategy": "shopify",
        "kind": "collection", "target_ref": "all", "tier": "base",
        "filter_json": {"vendors": ["Comoli Mens", "Auralee Mens"]}})
    assert r.status_code == 201, r.text

    spec = db.get_filter(db.get_watch(r.json()["watch"]["id"]))
    assert spec["vendors"] == ["Comoli Mens", "Auralee Mens"]


def test_the_filter_matches_the_store_spelling_it_was_built_from():
    from monitor.filters import matches
    spec = {"vendors": ["Comoli Mens", "Auralee Mens"]}
    assert matches({"vendor": "COMOLI MENS"}, spec)
    assert not matches({"vendor": "Comoli Womens"}, spec)
    assert not matches({"vendor": "Ys by Yohji Yamamoto Womens"}, spec)
