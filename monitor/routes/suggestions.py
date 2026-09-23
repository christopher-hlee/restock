"""Stores worth watching that this app can actually watch."""
from urllib.parse import urlparse

from fastapi import APIRouter

from .. import db
from ..suggestions import STORES

router = APIRouter()


def _host(url: str) -> str:
    host = (urlparse(url or "").netloc or "").lower()
    return host[4:] if host.startswith("www.") else host


@router.get("/suggestions")
def list_suggestions():
    """Checked stores you are not already watching.

    A store you watch any part of is left out: the point is somewhere new,
    and a second suggestion for a shop already on the list is noise.
    """
    watched = {_host(w.get("url")) for w in db.list_watches()}
    return {"stores": [s for s in STORES if _host(s["url"]) not in watched]}
