"""Platform sniffing — powers the one-click add flow."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import strategies

router = APIRouter()


class DetectRequest(BaseModel):
    url: str


@router.post("/detect")
async def detect(body: DetectRequest):
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "URL must start with http:// or https://")

    # A share link is a redirect, not the page; identify what it points at,
    # and say what that is so the form can show the store's own URL.
    try:
        resolved = await strategies.resolve_share_link(url)
    except strategies.ShareLinkError as exc:
        raise HTTPException(422, str(exc))

    found = await strategies.detect(resolved)
    if not found:
        raise HTTPException(
            422,
            "No supported platform detected. Shopify stores are identified by "
            "probing /products.json; the site may be gating it or running "
            "something else.",
        )
    if resolved != url:
        found = {**found, "resolved_url": resolved}
    return found
