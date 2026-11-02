"""A link shared from Google's app is a redirect, not the page.

Detection reads the URL itself — a Shopify product is /products/<handle> — so a
share.google link answered "Nothing I recognise" however watchable the page
behind it was, and it is how links arrive from a phone.
"""
import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from monitor import db, strategies, telegram_bot
from monitor.strategies import ShareLinkError, resolve_share_link

SHARE = "https://share.google/hx9StfBVJePrIzzYN"
STORE = "https://www.satisfyrunning.com"
PRODUCT = f"{STORE}/products/peaceshell-climb-pants"


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    db.init_db()


@pytest.fixture
def client(fresh_db, monkeypatch):
    monkeypatch.setattr("monitor.config.API_KEY", "k")
    monkeypatch.setattr("monitor.main.API_KEY", "k")
    from monitor.main import app
    with TestClient(app) as c:
        c.headers.update({"Authorization": "Bearer k"})
        yield c


def product_json():
    return {"title": "PeaceShell Climb Pants", "handle": "peaceshell-climb-pants",
            "vendor": "Satisfy", "price": 34500, "available": True,
            "featured_image": "//cdn.shopify.com/p.jpg",
            "variants": [{"id": 1, "title": "M", "available": True, "price": 34500},
                         {"id": 2, "title": "L", "available": False, "price": 34500}]}


def store_behind_the_share(destination=None):
    respx.get(SHARE).mock(return_value=httpx.Response(
        302, headers={"Location": destination or
                      f"{PRODUCT}?variant=1&srsltid=AfmBOoq&utm_source=share"}))
    respx.get(f"{PRODUCT}.js").mock(return_value=httpx.Response(200, json=product_json()))


# --- the helper ---------------------------------------------------------------

GENTLE_MONSTER = "https://www.gentlemonster.com/us/en/item/0P0M4JBCDF0PC/futura02"


@respx.mock
async def test_the_real_share_google_chain_reaches_the_store():
    """Copied from a GitHub runner following this exact link on 2026-11-02.

    share.google does not go straight to the page: it passes through
    www.google.com/share.google first. The first version stopped there and
    returned the Google URL as if it were the product — a one-hop mock had
    hidden it.
    """
    respx.get(SHARE).mock(return_value=httpx.Response(
        302, headers={"Location": "https://www.google.com/share.google?q=hx9StfBVJePrIzzYN"}))
    respx.get("https://www.google.com/share.google?q=hx9StfBVJePrIzzYN").mock(
        return_value=httpx.Response(301, headers={"Location": GENTLE_MONSTER
            + "?srsltid=AYCX9vLTyNqy32DBFbTH7-oYcZiPrxaDqx2EaU_UQ9N33MpiICBqVIKs&shem=aimgspe,"}))

    assert await resolve_share_link(SHARE) == GENTLE_MONSTER


@respx.mock
async def test_a_share_link_becomes_the_page_without_its_tracking():
    store_behind_the_share()

    url = await resolve_share_link(SHARE)

    # ?variant= is the size the person was looking at, so it stays.
    assert url == f"{PRODUCT}?variant=1"


@respx.mock(assert_all_called=False)
async def test_a_store_url_costs_no_request_at_all():
    """No routes are mocked: any request would raise."""
    assert await resolve_share_link(PRODUCT) == PRODUCT


@respx.mock
async def test_a_meta_refresh_is_followed_like_a_redirect():
    respx.get(SHARE).mock(return_value=httpx.Response(
        200, text=f'<meta http-equiv="refresh" content="0; url={PRODUCT}">'))

    assert await resolve_share_link(SHARE) == PRODUCT


@respx.mock
async def test_googles_own_redirect_wrapper_is_unwrapped():
    respx.get(SHARE).mock(return_value=httpx.Response(
        302, headers={"Location": f"https://www.google.com/url?q={PRODUCT}&sa=D"}))

    assert await resolve_share_link(SHARE) == PRODUCT


@respx.mock
async def test_a_google_search_is_refused_with_what_to_do_instead():
    """Sharing from a results list gives a search, which is nothing to watch."""
    respx.get(SHARE).mock(return_value=httpx.Response(
        302, headers={"Location": "https://www.google.com/search?q=comoli+coat"}))

    with pytest.raises(ShareLinkError, match="share that page instead"):
        await resolve_share_link(SHARE)


@respx.mock
async def test_a_redirect_loop_stops_cleanly():
    route = respx.get(SHARE).mock(return_value=httpx.Response(
        302, headers={"Location": SHARE}))

    with pytest.raises(ShareLinkError, match="more than 5"):
        await resolve_share_link(SHARE)
    assert route.call_count == strategies.SHARE_MAX_HOPS + 1


@respx.mock
async def test_a_downgrade_to_http_is_not_followed():
    respx.get(SHARE).mock(return_value=httpx.Response(
        302, headers={"Location": "http://shop.example.com/products/x"}))

    with pytest.raises(ShareLinkError, match="not https"):
        await resolve_share_link(SHARE)


@respx.mock
async def test_an_unreachable_share_service_says_so():
    respx.get(SHARE).mock(side_effect=httpx.ConnectTimeout("slow"))

    with pytest.raises(ShareLinkError, match="could not open"):
        await resolve_share_link(SHARE)


# --- where people actually paste them ----------------------------------------

@respx.mock
async def test_add_in_telegram_watches_the_product_not_the_share_link(fresh_db):
    store_behind_the_share()

    reply = await telegram_bot.handle(f"/add {SHARE}")

    assert "Watching" in reply and "PeaceShell Climb Pants" in reply, reply
    (w,) = db.list_watches()
    assert w["url"] == f"{PRODUCT}?variant=1"
    assert (w["strategy"], w["kind"]) == ("shopify", "product")


@respx.mock
async def test_add_in_telegram_explains_a_search_link(fresh_db):
    respx.get(SHARE).mock(return_value=httpx.Response(
        302, headers={"Location": "https://www.google.com/search?q=comoli+coat"}))

    reply = await telegram_bot.handle(f"/add {SHARE}")

    assert "Google search" in reply
    assert db.list_watches() == [], "nothing watchable, so nothing created"


@respx.mock
def test_the_dashboard_add_stores_the_stores_own_url(client):
    store_behind_the_share()

    r = client.post("/api/watches", json={"url": SHARE, "tier": "base"})

    assert r.status_code == 201, r.text
    assert r.json()["watch"]["url"] == f"{PRODUCT}?variant=1"


@respx.mock
def test_identify_tells_the_form_where_the_link_went(client):
    store_behind_the_share()

    d = client.post("/api/detect", json={"url": SHARE}).json()

    assert d["resolved_url"] == f"{PRODUCT}?variant=1"
    assert d["kind"] == "product"


@respx.mock
def test_a_search_link_is_a_clear_422_on_the_dashboard(client):
    respx.get(SHARE).mock(return_value=httpx.Response(
        302, headers={"Location": "https://www.google.com/search?q=x"}))

    r = client.post("/api/watches", json={"url": SHARE, "tier": "base"})

    assert r.status_code == 422 and "Google search" in r.json()["detail"]
