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
   watch), or a page with or without schema.org Product data.

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
    handle = m.group(1)
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
    if not shopify_product(final):
        describe_page(final, body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
