#!/usr/bin/env python3
"""Where does a link go, and can this app watch what is there?

Run from anywhere with ordinary internet access. The `check-url` workflow runs
it on a GitHub runner, because the development container cannot reach share
links or storefronts. For one URL it:

1. follows redirects, at most five hops and https only, printing each hop.
   Share links (share.google, goo.gl, bit.ly) are a redirect to the real page;
   some answer with a meta refresh instead of a 3xx, which is followed too;
2. if the destination is a Shopify product, reads /products/<handle>.js and
   prints the title, vendor, price and every variant with whether it can be
   bought, which is exactly what a product watch will see;
3. otherwise says what it found: a Google search page (not something to
   watch), or a page with or without schema.org Product data;
4. for a store or collection URL instead of a product, reads the catalogue
   and, for every product published in the last two weeks, sets what the
   feed says beside what the product page shows a person: the feed's variant
   flags and tags, /products/<handle>.js, the page's schema.org
   availability, its buy button and any "Coming soon" in the buy form. Where
   the feed says buyable and the page does not, it asks the cart itself
   (an anonymous /cart/add.js) for up to three of them, which settles it;
5. when the app's own dependencies are installed (the workflow installs
   them), runs the app's real path on it: resolve_share_link, detect, then
   one check. That is exactly what /add would store and what the first sweep
   would see, rather than this script's approximation of it.

    python3 check-url.py https://share.google/…
"""
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
MAX_HOPS = 5


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Hand every 3xx back to the caller, so each hop can be printed."""
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(_NoRedirect)


def get(url, accept="text/html,application/json;q=0.9,*/*;q=0.8"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept,
                                               "Accept-Language": "en-US,en;q=0.9"})
    try:
        with OPENER.open(req, timeout=20) as r:
            return r.status, dict(r.headers), r.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        body = e.read(200_000).decode("utf-8", "replace") if e.fp else ""
        return e.code, dict(e.headers or {}), body
    except (urllib.error.URLError, OSError) as e:      # DNS, TLS, timeout
        return f"error ({getattr(e, 'reason', e)})", {}, ""


META_REFRESH = re.compile(
    r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\'][^"\']*url=([^"\'>]+)', re.I)


def follow(url):
    """Every hop as (status, url), and the final status, headers and body."""
    hops = []
    for _ in range(MAX_HOPS + 1):
        if not url.lower().startswith("https://"):
            print(f"  refusing non-https hop: {url}")
            return hops, None, {}, ""
        status, headers, body = get(url)
        hops.append((status, url))
        nxt = None
        if not isinstance(status, int):
            return hops, status, headers, body
        if 300 <= status < 400:
            nxt = headers.get("Location") or headers.get("location")
        elif status == 200:
            m = META_REFRESH.search(body[:20000])
            if m:
                nxt = html.unescape(m.group(1).strip())
        if not nxt:
            return hops, status, headers, body
        url = urllib.parse.urljoin(url, nxt)
    print(f"  more than {MAX_HOPS} redirects; stopping")
    return hops, None, {}, ""


def shopify_product(final):
    u = urllib.parse.urlparse(final)
    m = re.search(r"/products/([^/?#]+)", u.path)
    if not m:
        return False
    # Normalised to one encoding: Satisfy's handles carry a raw "™", which an
    # HTTP request line cannot hold.
    handle = urllib.parse.quote(urllib.parse.unquote(m.group(1)), safe="")
    status, _, body = get(f"https://{u.netloc}/products/{handle}.js",
                          accept="application/json")
    if status != 200:
        print(f"  /products/{handle}.js answered {status}")
        return False
    try:
        p = json.loads(body)
    except ValueError:
        print(f"  /products/{handle}.js is not JSON")
        return False
    # The store's currency, as the buyer sees it from this runner's region.
    _, _, cart = get(f"https://{u.netloc}/cart.js", accept="application/json")
    try:
        currency = json.loads(cart).get("currency")
    except ValueError:
        currency = None
    price = lambda cents: f"{cents / 100:,.2f}" if isinstance(cents, int) else str(cents)
    print("SHOPIFY PRODUCT — watchable")
    print(f"  store    : {u.netloc}")
    print(f"  url      : https://{u.netloc}/products/{handle}")
    print(f"  title    : {p.get('title')}")
    print(f"  vendor   : {p.get('vendor')}")
    print(f"  type     : {p.get('type')}")
    print(f"  price    : {price(p.get('price'))} {currency or ''}".rstrip())
    print(f"  buyable  : {p.get('available')}")
    print(f"  published: {p.get('published_at')}")
    print("  variants :")
    for v in p.get("variants") or []:
        print(f"    {'BUYABLE ' if v.get('available') else 'sold out'}  "
              f"{v.get('title')!s:<24} {price(v.get('price'))}")
    return True


def describe_page(final, body):
    u = urllib.parse.urlparse(final)
    if u.netloc.endswith("google.com") and u.path.startswith("/search"):
        q = urllib.parse.parse_qs(u.query).get("q", [""])[0]
        print("GOOGLE SEARCH PAGE — not a store page, nothing to watch")
        print(f"  query: {q}")
        return
    title = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    site = re.search(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)', body, re.I)
    ogt = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', body, re.I)
    shopify = "cdn.shopify.com" in body or "Shopify.theme" in body
    product_ld = re.search(r'"@type"\s*:\s*"Product"', body) is not None
    print("PAGE")
    print(f"  host       : {u.netloc}")
    print(f"  title      : {html.unescape((title.group(1) if title else '').strip())[:160]}")
    print(f"  og:title   : {html.unescape(ogt.group(1)) if ogt else '-'}")
    print(f"  site       : {html.unescape(site.group(1)) if site else '-'}")
    print(f"  shopify    : {'yes' if shopify else 'no sign of it'}")
    print(f"  schema.org : {'Product data present' if product_ld else 'no Product data'}")


# ---------------------------------------------------------------- collections

import time
from datetime import datetime, timedelta, timezone

RECENT_DAYS = 14
MARKER = re.compile(r"soon|launch|coming|pre-?order|upcoming|release|drop", re.I)
LD = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.I | re.S)
FORM = re.compile(r'<form[^>]+action=["\'][^"\']*/cart/add[^"\']*["\'][^>]*>(.*?)</form>', re.I | re.S)
BUTTON = re.compile(r'<button[^>]*(?:name=["\']add["\']|type=["\']submit["\'])[^>]*>.*?</button>', re.I | re.S)


def is_listing(url):
    path = urllib.parse.urlparse(url).path.rstrip("/")
    return path == "" or re.fullmatch(r"/collections/[^/]+", path) is not None


def jget(url):
    status, _, body = get(url, accept="application/json")
    try:
        return status, json.loads(body)
    except (ValueError, TypeError):
        return status, None


def page_view(base, handle):
    """What a person sees: the buy form, its button, and the page's offers."""
    status, _, body = get(f"{base}/products/{urllib.parse.quote(handle, safe='')}")
    if status != 200:
        return {"page": status}
    forms = FORM.findall(body)
    form = max(forms, key=len) if forms else ""
    buttons = BUTTON.findall(form)
    button = buttons[0] if buttons else ""
    text = re.sub(r"<[^>]+>", " ", button)
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    ld = []
    for block in LD.findall(body):
        ld += re.findall(r'"availability"\s*:\s*"([^"]+)"', block)
    return {
        "page": status,
        "form": bool(form),
        "button": text[:40] or "-",
        "disabled": bool(re.search(r"\sdisabled(\s|=|>)", button)),
        "form_soon": bool(re.search(r"coming\s+soon", form, re.I)),
        "form_notify": bool(re.search(r"notify\s+me", form, re.I)),
        "page_soon": len(re.findall(r"coming\s+soon", body, re.I)),
        "ld": sorted({a.rsplit("/", 1)[-1] for a in ld}) or ["-"],
        "button_html": re.sub(r"\s+", " ", button)[:300],
    }


def cart_accepts(base, variant_id):
    """Ask the cart, which is the only source that cannot be decorative."""
    body = json.dumps({"items": [{"id": variant_id, "quantity": 1}]}).encode()
    req = urllib.request.Request(f"{base}/cart/add.js", data=body, method="POST",
                                 headers={"User-Agent": UA, "Content-Type": "application/json",
                                          "Accept": "application/json"})
    try:
        with OPENER.open(req, timeout=20) as r:
            return r.status, "added"
    except urllib.error.HTTPError as e:
        try:
            d = json.loads(e.read(20000).decode("utf-8", "replace"))
            return e.code, d.get("description") or d.get("message") or str(d)[:120]
        except ValueError:
            return e.code, "(no JSON)"
    except (urllib.error.URLError, OSError) as e:
        return "error", str(getattr(e, "reason", e))


def collection_view(final):
    u = urllib.parse.urlparse(final)
    base = f"https://{u.netloc}"
    path = u.path.rstrip("/")
    feed = f"{base}{path}/products.json" if path.startswith("/collections/") else f"{base}/products.json"
    products, page = [], 1
    while page <= 10:
        status, data = jget(f"{feed}?limit=250&page={page}")
        if status != 200 or not isinstance(data, dict):
            print(f"  {feed} page {page} answered {status}")
            break
        rows = data.get("products") or []
        products += rows
        if len(rows) < 250:
            break
        page += 1
        time.sleep(1.2)
    print(f"CATALOGUE — {len(products)} products in {feed}")
    since = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)

    def published(p):
        try:
            return datetime.fromisoformat((p.get("published_at") or "").replace("Z", "+00:00"))
        except ValueError:
            return None

    recent = [p for p in products if (published(p) or since) > since]
    recent.sort(key=lambda p: published(p) or since, reverse=True)
    print(f"  {len(recent)} published in the last {RECENT_DAYS} days\n")

    disagree, rows = [], []
    for p in recent[:60]:
        h = p.get("handle")
        vs = [v for v in p.get("variants") or [] if v.get("id")]
        t = sum(1 for v in vs if v.get("available") is True)
        f = sum(1 for v in vs if v.get("available") is False)
        m = sum(1 for v in vs if "available" not in v)
        tags = p.get("tags") or []
        tags = tags if isinstance(tags, list) else [x.strip() for x in str(tags).split(",")]
        flagged = [x for x in tags if MARKER.search(x)]
        time.sleep(1.2)
        js_status, js = jget(f"{base}/products/{urllib.parse.quote(h, safe='')}.js")
        js_avail = js.get("available") if isinstance(js, dict) else f"({js_status})"
        time.sleep(1.2)
        pv = page_view(base, h)
        feed_buyable = t > 0 or (m > 0 and f == 0)
        page_says_no = pv.get("form_soon") or pv.get("disabled") or not pv.get("form") \
            or (pv.get("ld") and "InStock" not in pv["ld"] and pv["ld"] != ["-"])
        row = dict(handle=h, title=p.get("title"), published=p.get("published_at"),
                   created=p.get("created_at"), feed=f"{t}/{f}/{m}", js=js_avail,
                   tags=flagged, **pv)
        rows.append(row)
        if feed_buyable and page_says_no:
            disagree.append((row, vs))
        print(f"{h}")
        print(f"   {p.get('title')} · published {p.get('published_at')} · created {p.get('created_at')}")
        print(f"   feed variants true/false/missing {t}/{f}/{m} · .js available {js_avail} · "
              f"marker tags {flagged or '-'}")
        print(f"   page {pv.get('page')} · form {pv.get('form')} · button '{pv.get('button')}'"
              f"{' DISABLED' if pv.get('disabled') else ''} · form says coming soon "
              f"{pv.get('form_soon')} · notify {pv.get('form_notify')} · "
              f"page 'coming soon' x{pv.get('page_soon')} · schema {pv.get('ld')}")
    print(f"\nall tags seen on recent products: "
          f"{sorted({x for p in recent for x in (p.get('tags') or [])})[:80]}")

    print(f"\nFEED SAYS BUYABLE, PAGE DOES NOT: {len(disagree)} of {len(rows)}")
    for row, vs in disagree[:3]:
        vid = next((v["id"] for v in vs if v.get("available") is not False), vs[0]["id"] if vs else None)
        time.sleep(1.2)
        status, why = cart_accepts(base, vid) if vid else ("-", "no variant")
        print(f"  {row['handle']}: cart/add.js -> {status} {why}")
        print(f"    page {row.get('page')} · button html: {row.get('button_html', '-')}")
    return 0


def app_view(url):
    """The app's own answer, through the code the server runs."""
    try:
        import asyncio
        sys.path.insert(0, ".")
        from monitor import strategies
        from monitor.fetcher import close_client
    except ImportError as exc:
        print(f"\n(app dependencies not installed, skipping the app's view: {exc})")
        return 0

    async def run():
        print("\nTHE APP'S VIEW — what /add stores and the first check sees")
        try:
            resolved = await strategies.resolve_share_link(url)
        except strategies.ShareLinkError as exc:
            print(f"  refused: {exc}")
            return 1
        print(f"  resolved : {resolved}")
        found = await strategies.detect(resolved)
        if not found:
            print("  detect   : nothing recognised — /add would refuse it")
            return 1
        for k in ("strategy", "kind", "name", "brand", "target_ref", "detected_via"):
            if found.get(k):
                print(f"  {k:<9}: {found[k]}")
        watch = {"id": 0, "url": found.get("url") or resolved,
                 "strategy": found.get("strategy"), "kind": found.get("kind") or "product",
                 "target_ref": found.get("target_ref"), "name": found.get("name")}
        r = await strategies.check(watch)
        print(f"  check ok : {r.ok}   http {r.http_status}")
        if not r.ok:
            print(f"  error    : {r.error}")
            return 1
        print(f"  state    : {r.state}")
        print(f"  title    : {r.title}")
        print(f"  price    : {r.price}")
        extra = r.extra or {}
        if extra.get("availability"):
            print(f"  schema   : {', '.join(extra['availability'])}"
                  f"{'  (preorder)' if extra.get('preorder') else ''}")
        for o in (extra.get("offers") or [])[:12]:
            print(f"    offer  : {o.get('title')}  {o.get('price')}")
        await close_client()
        return 0

    return asyncio.run(run())


def main():
    if len(sys.argv) != 2:
        print("usage: check-url.py <url>")
        return 2
    url = sys.argv[1].strip()
    hops, status, headers, body = follow(url)
    print("hops:")
    for s, h in hops:
        print(f"  {s}  {h}")
    if status is None:
        return 1
    final = hops[-1][1]
    print(f"final: {status} {final}\n")
    if status != 200:
        print(f"the destination answered {status}")
        return 1
    if is_listing(final):
        return collection_view(final)
    if not shopify_product(final):
        describe_page(final, body)
    return app_view(url)


if __name__ == "__main__":
    sys.exit(main())
