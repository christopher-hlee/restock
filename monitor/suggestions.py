"""Stores the dashboard suggests watching.

Every entry was checked from a GitHub runner by check-suggestions.py on
2026-09-23: its /products.json answered this app (the endpoint every
collection watch sweeps), and `brands` is counted from the vendor field of
the first 1,000 products it returned, not taken from a stockist list.

`vendors` is the store's own spelling, because a vendor filter matches it
exactly (ignoring case): Neighbour sells "Comoli Mens", and its "Yohji" is
Y's, the women's line, so it is not offered as Yohji. Stores whose catalogue
was open but carried none of these brands, and stores that refused the feed
(HAVEN, Nepenthes, Norse Store, Nitty Gritty, Blue in Green), are left out.

Re-run the `suggestions` workflow to refresh the counts.
"""
CHECKED = "2026-09-23"

STORES: list[dict] = [
    {"name": "Neighbour", "city": "Vancouver",
     "url": "https://shopneighbour.com/collections/all",
     "sale_url": "https://shopneighbour.com/collections/sale",
     "brands": [{"name": "COMOLI", "count": 20}, {"name": "AURALEE", "count": 16}],
     "vendors": ["Comoli Mens", "Auralee Mens"],
     "products": 1000, "checked": CHECKED},
    {"name": "Très Bien", "city": "Malmö",
     "url": "https://tres-bien.com/collections/all",
     "sale_url": "https://tres-bien.com/collections/sale",
     "brands": [{"name": "AURALEE", "count": 46}],
     "vendors": ["Auralee"],
     "products": 1000, "checked": CHECKED},
    {"name": "Mohawk General Store", "city": "Los Angeles",
     "url": "https://mohawkgeneralstore.com/collections/all",
     "sale_url": "https://mohawkgeneralstore.com/collections/sale",
     "brands": [{"name": "AURALEE", "count": 39}, {"name": "COMOLI", "count": 3}],
     "vendors": ["Auralee", "Comoli"],
     "products": 1000, "checked": CHECKED},
    {"name": "Oi Polloi", "city": "Manchester",
     "url": "https://www.oipolloi.com/collections/all",
     "sale_url": "https://www.oipolloi.com/collections/sale",
     "brands": [{"name": "Goldwin", "count": 25}, {"name": "and wander", "count": 10}],
     "vendors": ["Goldwin", "And Wander"],
     "products": 1000, "checked": CHECKED},
    {"name": "Standard & Strange", "city": "Oakland",
     "url": "https://standardandstrange.com/collections/all",
     "sale_url": "https://standardandstrange.com/collections/sale",
     "brands": [{"name": "and wander", "count": 3}],
     "vendors": ["And Wander"],
     "products": 1000, "checked": CHECKED},
    {"name": "Namu Shop", "city": "Portland",
     "url": "https://namu-shop.com/collections/all",
     "sale_url": "https://namu-shop.com/collections/sale",
     "brands": [{"name": "AURALEE", "count": 93}],
     "vendors": ["Auralee"],
     "products": 1000, "checked": CHECKED},
]
