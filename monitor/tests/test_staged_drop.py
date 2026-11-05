"""A drop that is on sale everywhere but the page.

On 2026-11-05 Satisfy put thirteen products on sale in its feed, its product
API and its schema.org data. A runner's /cart/add.js call accepted each one,
but every product page still showed a Coming Soon button. The alert said
"released" and sent you to a page with nothing to press. The alert should
still fire, because the cart really does take the order, but it should say
what the page says.
"""
import json
import re
from datetime import timedelta

import httpx
import pytest
import respx

from monitor import db, scheduler
from monitor.notify.telegram import render
from monitor.statemachine import ARRIVAL_LAUNCHED, NEW_PRODUCT
from monitor.strategies.shopify import page_coming_soon
from monitor.timeutil import stamp, utcnow

STORE = "https://www.satisfyrunning.com"
FEED = f"{STORE}/products.json"
PAGE = re.compile(rf"^{re.escape(STORE)}/products/[^/.?]+$")
OLD = (utcnow() - timedelta(days=60)).isoformat()

# Copied from the runner's read of /products/mothtech-long-tee-cl that morning.
SATISFY_SOON = (
    '<form method="post" action="/cart/add" id="product-form-template--24212255998280__main">'
    '<button id="ProductNotifyMeButton-template--24212255998280__main" type="submit" '
    'name="notify" class="product-form__submit button button--full-width '
    'text-body-btn-primary button--primary" data-coming-soon="true" '
    'data-coming-soon-newsletter="true" > <span>Coming Soon </span></button></form>')
RELATED_CARD = ('<div class="card"><p class="card_information__bicolumn '
                'subtitle-simon-sm"> COMING SOON </p>'
                '<button id="quick-add-template--1__related-123" name="add" '
                'data-coming-soon="true">Coming soon</button></div>')
LIVE = ('<form method="post" action="/cart/add">'
        '<button id="ProductSubmitButton-template--24212255998280__main" type="submit" '
        'name="add" class="product-form__submit button"> <span>Add to cart</span>'
        '</button></form>')


# --- reading the page ---------------------------------------------------------

def test_satisfys_real_coming_soon_button_is_recognised():
    assert page_coming_soon(SATISFY_SOON) is True


def test_a_related_items_badge_does_not_speak_for_this_product():
    """The live page lists other products, some of them coming soon."""
    assert page_coming_soon(LIVE + RELATED_CARD) is False


def test_a_coming_soon_label_without_the_flag_still_counts():
    assert page_coming_soon('<button type="submit" name="add" class="product-form__submit">'
                            '<span>Coming soon</span></button>') is True


# --- the alert ----------------------------------------------------------------

def entry(handle):
    return {"handle": handle, "title": handle.replace("-", " ").title(),
            "published_at": OLD, "created_at": OLD,
            "variants": [{"id": abs(hash(handle)) % 9999 + 1, "title": "M",
                          "price": "110.00", "available": True}]}


HANDLES = [f"drop-item-{i:02d}-cl" for i in range(13)]


@pytest.fixture
def sent(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    db.init_db()
    calls = []

    async def fake(watch, kind, payload):
        calls.append(payload)

    monkeypatch.setattr("monitor.notify.telegram.send_event", fake)
    monkeypatch.setattr("monitor.notify.telegram.configured", lambda: True)
    return calls


def coming_soon_watch():
    ledger = {h: {"available": False} for h in HANDLES}
    return db.create_watch(
        name="satisfyrunning.com · all products", brand="satisfyrunning.com",
        url=STORE, strategy="shopify", kind="collection", target_ref=None,
        last_state="watching", baseline_json=json.dumps(sorted(ledger)),
        availability_json=json.dumps(ledger), last_sweep_at=stamp())


def the_drop():
    respx.get(url__startswith=FEED).mock(return_value=httpx.Response(
        200, json={"products": [entry(h) for h in HANDLES]}))


@respx.mock
async def test_a_staged_drop_is_announced_as_buyable_early(sent):
    wid = coming_soon_watch()
    the_drop()
    pages = respx.get(url__regex=PAGE).mock(
        return_value=httpx.Response(200, text=SATISFY_SOON + RELATED_CARD))

    await scheduler.check_watch(db.get_watch(wid))

    (alert,) = [p for p in sent if p.get("arrival") == ARRIVAL_LAUNCHED]
    assert len(alert["handles"]) == 13
    assert pages.call_count == scheduler.PAGE_SAMPLE == 3, \
        "a forty-item drop must not cost forty page reads"
    assert alert["page_coming_soon"]["soon"] == alert["page_coming_soon"]["checked"]

    text = render(db.get_watch(wid), NEW_PRODUCT, alert)
    assert "13 buyable early" in text
    assert "released" not in text
    assert "still say Coming soon" in text
    # The dashboard reads the same payload from the stored event.
    (row,) = [e for e in db.list_events() if e["kind"] == NEW_PRODUCT]
    assert row["payload"]["page_coming_soon"] == alert["page_coming_soon"]


@respx.mock
async def test_a_live_drop_keeps_its_released_headline(sent):
    wid = coming_soon_watch()
    the_drop()
    respx.get(url__regex=PAGE).mock(return_value=httpx.Response(200, text=LIVE + RELATED_CARD))

    await scheduler.check_watch(db.get_watch(wid))

    (alert,) = sent
    text = render(db.get_watch(wid), NEW_PRODUCT, alert)
    assert "13 released" in text and "Coming soon" not in text


@respx.mock
async def test_a_page_that_cannot_be_read_never_costs_the_alert(sent):
    wid = coming_soon_watch()
    the_drop()
    respx.get(url__regex=PAGE).mock(return_value=httpx.Response(503))

    await scheduler.check_watch(db.get_watch(wid))

    (alert,) = sent
    assert "page_coming_soon" not in alert, "nothing was read, so nothing is claimed"
    assert "13 released" in render(db.get_watch(wid), NEW_PRODUCT, alert)


def test_a_mixed_sample_is_reported_as_counted():
    payload = {"handles": ["a", "b"], "arrival": ARRIVAL_LAUNCHED, "first_sale": ["a", "b"],
               "titles": {"a": "A", "b": "B"},
               "page_coming_soon": {"checked": ["a", "b"], "soon": ["a"]}}
    text = render({"name": "s", "brand": "s.com", "kind": "collection"}, NEW_PRODUCT, payload)
    assert "2 released" in text
    assert "1 of the 2 pages I checked still say Coming soon" in text
