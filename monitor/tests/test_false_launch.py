"""A sweep that does not state availability must not change it.

Two ways a product could be announced as "released" or "back in stock"
without anything having gone on sale:

1. The Atom fallback. It runs when products.json fails, and it has no
   variants, so it cannot say whether anything is buyable. The ledger recorded
   every item it listed as unavailable anyway, and the next products.json
   sweep then announced each buyable product as a launch.
2. Variants with no `available` flag. The feed reader counts them as
   buyable, which is the right default for building cart links and the wrong
   evidence for announcing a release.
"""
import json
from datetime import timedelta

import httpx
import pytest
import respx

from monitor import db, scheduler
from monitor.statemachine import ARRIVAL_LAUNCHED
from monitor.timeutil import stamp, utcnow

STORE = "https://www.satisfyrunning.com"
FEED = f"{STORE}/products.json"
ATOM = f"{STORE}/collections/all.atom"
OLD = (utcnow() - timedelta(days=60)).isoformat()


def entry(handle, *, available="unset"):
    variant = {"id": abs(hash(handle)) % 9999 + 1, "title": "M", "price": "110.00"}
    if available != "unset":
        variant["available"] = available
    return {"handle": handle, "title": handle.replace("-", " ").title(),
            "published_at": OLD, "created_at": OLD, "variants": [variant]}


def atom(*handles):
    entries = "".join(
        f'<entry><title>{h}</title><link href="{STORE}/products/{h}"/>'
        f'<published>{OLD}</published></entry>' for h in handles)
    return httpx.Response(200, text=f'<feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>')


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


def watch(ledger):
    return db.create_watch(
        name="satisfyrunning.com · all products", brand="satisfyrunning.com",
        url=STORE, strategy="shopify", kind="collection", target_ref=None,
        last_state="watching", baseline_json=json.dumps(sorted(ledger)),
        availability_json=json.dumps(ledger), last_sweep_at=stamp())


async def sweep(wid):
    await scheduler.check_watch(db.get_watch(wid))


def launches(sent):
    return [p for p in sent if p.get("arrival") == ARRIVAL_LAUNCHED]


@respx.mock
async def test_an_atom_sweep_does_not_arm_a_false_restock(sent):
    """On sale, then one Atom read, then on sale again: nothing happened."""
    wid = watch({"tee": {"available": True, "ever_buyable": True}})
    route = respx.get(url__startswith=FEED)
    route.side_effect = [
        httpx.Response(403),                                   # gated once
        httpx.Response(200, json={"products": [entry("tee", available=True)]}),
    ]
    respx.get(url__startswith=ATOM).mock(return_value=atom("tee"))

    await sweep(wid)                     # products.json refused → Atom
    ledger = db.get_availability(db.get_watch(wid))
    assert ledger["tee"]["available"] is True, \
        "a read with no availability in it recorded the product as sold out"

    await sweep(wid)                     # products.json again, unchanged
    assert launches(sent) == [], "announced a restock that never happened"


@respx.mock
async def test_variants_with_no_flag_are_not_announced_as_released(sent):
    """Coming soon (stated false), then the flag disappears: not a release."""
    wid = watch({"cap-cl": {"available": False}})
    respx.get(url__startswith=FEED).mock(return_value=httpx.Response(
        200, json={"products": [entry("cap-cl")]}))    # no `available` at all

    await sweep(wid)

    assert launches(sent) == []
    assert db.get_availability(db.get_watch(wid))["cap-cl"]["available"] is False


@respx.mock
async def test_a_stated_flip_still_announces_once(sent):
    """The guard must not swallow the real thing."""
    wid = watch({"cap-cl": {"available": False}})
    respx.get(url__startswith=FEED).mock(return_value=httpx.Response(
        200, json={"products": [entry("cap-cl", available=True)]}))

    await sweep(wid)

    (alert,) = launches(sent)
    assert alert["handles"] == ["cap-cl"]
    assert alert["first_sale"] == ["cap-cl"], "never seen on sale: a release"
