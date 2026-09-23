#!/usr/bin/env python3
"""Which candidate stores can this app actually watch, and what do they carry?

Run from anywhere with ordinary internet access (the `suggestions` workflow
runs it on a GitHub runner, since the development container cannot reach
storefronts). For each candidate it asks the two questions that decide
whether a store belongs in the dashboard's suggestions:

1. Is the catalogue open?  GET /products.json — the endpoint every collection
   watch sweeps. Shopify Plus stores often refuse it (Haven does), and a store
   that refuses it cannot be watched however good it is.
2. Does it carry the brands you buy?  Counted from the `vendor` field of up to
   1,000 products, not assumed from a stockist list that is a season stale.

It also tries /collections/sale, the collection worth watching with a vendor
filter. Prints a table and writes suggestions-checked.json.
"""
import json
import sys
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
BRANDS = {
    "AURALEE": ("auralee",),
    "COMOLI": ("comoli",),
    "and wander": ("and wander", "and-wander", "andwander"),
    "Goldwin": ("goldwin",),
    "Yohji Yamamoto": ("yohji",),
    "Satisfy": ("satisfy",),
}
CANDIDATES = [
    ("Blue in Green SOHO", "bluingreensoho.com", "New York"),
    ("Mohawk General Store", "mohawkgeneralstore.com", "Los Angeles"),
    ("Hatchet Outdoor Supply", "hatchetsupply.com", "Los Angeles"),
    ("Nepenthes New York", "nepenthesny.com", "New York"),
    ("Lost & Found", "lostandfoundshop.com", "Los Angeles"),
    ("No Man Walks Alone", "nomanwalksalone.com", "New York"),
    ("Snake Oil Provisions", "snakeoilprovisions.com", "Portland"),
    ("Stag Provisions", "stagprovisions.com", "Austin"),
    ("Standard & Strange", "standardandstrange.com", "Oakland"),
    ("Neighbour", "shopneighbour.com", "Vancouver"),
    ("Livestock", "deadstock.ca", "Vancouver"),
    ("Oi Polloi", "www.oipolloi.com", "Manchester"),
    ("Norse Store", "www.norsestore.com", "Copenhagen"),
    ("Goodhood", "goodhoodstore.com", "London"),
    ("Nitty Gritty", "www.nittygrittystore.com", "Stockholm"),
    ("Très Bien", "tres-bien.com", "Malmö"),
    ("HAVEN", "havenshop.com", "Vancouver"),
    ("Namu Shop", "namu-shop.com", "Portland"),
]
PAGES = 4


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read()
            try:
                return r.status, json.loads(body)
            except ValueError:
                return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:                      # DNS, TLS, timeout
        return type(e).__name__, None


def check(name, host, city):
    base = f"https://{host}"
    status, data = get(f"{base}/products.json?limit=250")
    out = {"name": name, "host": host, "city": city, "status": status,
           "open": False, "products": 0, "brands": {}, "vendors": {},
           "sale": None}
    if not (status == 200 and isinstance(data, dict)
            and isinstance(data.get("products"), list)):
        return out
    out["open"] = True
    products = list(data["products"])
    page = 2
    while len(data.get("products") or []) == 250 and page <= PAGES:
        time.sleep(1.2)
        _, data = get(f"{base}/products.json?limit=250&page={page}")
        data = data if isinstance(data, dict) else {}
        products += data.get("products") or []
        page += 1
    out["products"] = len(products)
    for p in products:
        vendor = (p.get("vendor") or "").lower()
        for brand, needles in BRANDS.items():
            if any(n in vendor for n in needles):
                out["brands"][brand] = out["brands"].get(brand, 0) + 1
                # The exact spelling, because a vendor filter matches it
                # exactly: "Yohji Yamamoto POUR HOMME" is not "Yohji Yamamoto".
                exact = (p.get("vendor") or "").strip()
                out["vendors"][exact] = out["vendors"].get(exact, 0) + 1
    time.sleep(1.2)
    s_status, s_data = get(f"{base}/collections/sale/products.json?limit=1")
    out["sale"] = (s_status == 200 and isinstance(s_data, dict)
                   and isinstance(s_data.get("products"), list))
    return out


def main():
    only = set(sys.argv[1:])
    results = []
    for name, host, city in CANDIDATES:
        if only and host not in only:
            continue
        r = check(name, host, city)
        results.append(r)
        brands = ", ".join(f"{b} {n}" for b, n in sorted(r["brands"].items(),
                                                         key=lambda x: -x[1]))
        print(f"{'OPEN ' if r['open'] else 'SHUT '} {name:24} {str(r['status']):>5}"
              f"  {r['products']:>5} products  sale={r['sale']}  {brands}"
              f"  vendors={json.dumps(r['vendors'], ensure_ascii=False)}",
              flush=True)
        time.sleep(1.5)
    with open("suggestions-checked.json", "w") as f:
        json.dump(results, f, indent=1)
    return 0 if any(r["open"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
