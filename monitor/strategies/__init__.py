"""Strategy registry and platform auto-detection.

Adding a watch should be paste-a-URL simple, so `detect` sniffs the platform
rather than making you pick one. Retailer-specific strategies match on hostname
first; Shopify is the generic fallback because it's identified by probing
endpoints rather than by domain.
"""
import html
import re
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import httpx

from ..fetcher import get_client
from ..statemachine import CheckResult
from . import announce, bestbuy, retail, shopify, target

REGISTRY = {
    shopify.NAME: shopify,
    target.NAME: target,
    bestbuy.NAME: bestbuy,
    announce.NAME: announce,
    retail.NAME: retail,
}

# Hostname-matched strategies are cheap to rule out, so try them first. announce
# precedes shopify because a store's /search URL would otherwise be claimed as a
# collection watch by shopify's origin probe.
#
# retail is LAST on purpose. It reads schema.org JSON-LD, which Shopify product
# pages publish too — so placing it any earlier would quietly claim every
# Shopify watch and give up per-variant availability and cart permalinks for a
# strictly worse reading. It is the fallback for the storefronts nothing else
# understands, which is most of them.
DETECT_ORDER = (target, bestbuy, announce, shopify, retail)


async def check(watch: dict) -> CheckResult:
    strategy = REGISTRY.get(watch.get("strategy"))
    if strategy is None:
        return CheckResult(ok=False,
                           error=f"unknown strategy {watch.get('strategy')!r}")
    return await strategy.check(watch)


async def detect(url: str) -> dict | None:
    for strategy in DETECT_ORDER:
        try:
            found = await strategy.detect(url)
        except Exception as exc:  # a broken sniffer must not block the others
            continue
        if found:
            return found
    return None


# ---------------------------------------------------------------- share links

# Sharing a page from Google's app gives a share.google link, not the page.
# Detection reads the URL itself (a Shopify product is /products/<handle>), so
# a share link was "Nothing I recognise" however watchable the page behind it.
SHARE_HOSTS = {"share.google", "goo.gl", "g.co", "search.app", "bit.ly"}
SHARE_MAX_HOPS = 5
# Query parameters a share adds that say nothing about the product. The rest
# stay: ?variant= is the size the person was looking at.
_TRACKING = re.compile(r"^(utm_.*|srsltid|shem|gclid|gbraid|wbraid|fbclid|_pos|_sid|_ss)$", re.I)
_META_REFRESH = re.compile(
    r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\'][^"\']*url=([^"\'>]+)', re.I)

GOOGLE_SEARCH_MESSAGE = (
    "That share link opens a Google search, not a store page, so there is no "
    "product in it to watch. Open it, tap the store's result, and share that "
    "page instead.")


class ShareLinkError(ValueError):
    """A share link that does not lead to something watchable. The message is
    written for the person, and is safe to show them as it stands."""


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _is_google(host: str) -> bool:
    return host == "google.com" or host.startswith("google.") or host.endswith(".google.com")


def _is_share_hop(url: str) -> bool:
    """A step on the way to the page rather than the page.

    share.google does not go straight to the store: it answers with
    www.google.com/share.google?q=<id>, and that hop redirects to the page.
    Stopping at the first host outside SHARE_HOSTS returned that Google URL
    as if it were the product.
    """
    host = _host(url)
    return host in SHARE_HOSTS or (_is_google(host)
                                   and urlparse(url).path == "/share.google")


def _clean(url: str) -> str:
    u = urlparse(url)
    query = [(k, v) for k, vs in parse_qs(u.query, keep_blank_values=True).items()
             for v in vs if not _TRACKING.match(k)]
    return urlunparse(u._replace(query=urlencode(query), fragment=""))


async def resolve_share_link(url: str) -> str:
    """The page a share link points at; any other URL, untouched.

    Only hosts in SHARE_HOSTS are followed, so pasting a store's own URL costs
    no request at all. Redirects are followed by hand (https only, at most five
    hops, meta refreshes included) so a loop or a downgrade to http stops here
    rather than inside detection. Raises ShareLinkError when the link leads
    nowhere watchable — above all a Google search page, which is what sharing
    from a results list produces.
    """
    if _host(url) not in SHARE_HOSTS:
        return url
    client = get_client()
    current = url
    for _ in range(SHARE_MAX_HOPS + 1):
        if not current.lower().startswith("https://"):
            raise ShareLinkError("That share link leads somewhere that is not https, "
                                 "so I did not follow it.")
        host = _host(current)
        if _is_google(host) and urlparse(current).path == "/url":
            # Google's own redirect wrapper: the destination is in the query.
            q = parse_qs(urlparse(current).query)
            inner = (q.get("q") or q.get("url") or [""])[0]
            if inner.startswith("https://"):
                current = inner
                continue
        if _is_google(host) and urlparse(current).path.startswith("/search"):
            raise ShareLinkError(GOOGLE_SEARCH_MESSAGE)
        if not _is_share_hop(current):
            return _clean(current)
        try:
            resp = await client.get(current, follow_redirects=False,
                                    headers={"Accept": "text/html,*/*;q=0.8"})
        except httpx.HTTPError as exc:
            raise ShareLinkError(f"I could not open that share link "
                                 f"({type(exc).__name__}). Open it and share "
                                 f"the store page itself instead.") from exc
        nxt = resp.headers.get("location") if resp.is_redirect else None
        if not nxt and resp.status_code == 200:
            m = _META_REFRESH.search(resp.text[:20000])
            nxt = html.unescape(m.group(1).strip()) if m else None
        if not nxt:
            raise ShareLinkError("That share link did not lead to a page "
                                 f"(the link service answered {resp.status_code}).")
        current = urljoin(current, nxt)
    raise ShareLinkError(f"That share link redirects more than {SHARE_MAX_HOPS} "
                         f"times, so I stopped following it.")
