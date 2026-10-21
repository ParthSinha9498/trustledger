"""Proxy from the cockpit to the brand node's supply chain endpoint. Owned by the cockpit work
stream; router included in api/main.py."""
import httpx
from fastapi import APIRouter, HTTPException

from backend import config
from backend.common import http

router = APIRouter(prefix="/supply-chain", tags=["supply-chain"])


@router.get("")
def supply_chain(sku: str | None = None, store_id: str | None = None):
    params = {"brand_id": config.brand_id()}
    if sku:
        params["sku"] = sku
    if store_id:
        params["store_id"] = store_id
    try:
        with http.client(config.brand_node_url()) as c:
            r = c.get("/v1/supply-chain", params=params)
    except httpx.HTTPError as e:
        raise HTTPException(502, {"error": "brand node unreachable", "detail": str(e)})
    if r.status_code != 200:
        try:
            detail = r.json().get("detail")
        except ValueError:
            detail = r.text
        raise HTTPException(r.status_code if r.status_code < 500 else 502, detail)
    return r.json()
