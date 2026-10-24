"""Cockpit overview data: failed authenticity checks over time, by reason and by store.

The api never reads the brand database. It asks the brand node through its existing aggregate query API
(`POST /v1/query`, metric verification_failures), which returns exact business counts (no buyer data, no
privacy budget). These are all NOT_VERIFIED answers in the brand's verification log: a live one blocks the checkout
before any PayPal order exists; the seeded clone attempts never became checkouts.
Store display names come from the platform's own `stores` table.
"""
import httpx
from fastapi import APIRouter, HTTPException, Query

from backend import config, db
from backend.common import http

router = APIRouter(prefix="/cockpit", tags=["cockpit"])


def _failures(group_by: list[str], week_from: int) -> list[dict]:
    body = {"brand_id": config.brand_id(), "purpose": "cockpit",
            "spec": {"metric": "verification_failures", "group_by": group_by, "filters": {"week_from": week_from}}}
    try:
        with http.client(config.brand_node_url()) as c:
            r = c.post("/v1/query", json=body)
    except httpx.HTTPError as e:
        raise HTTPException(502, {"error": "brand node unreachable", "detail": str(e)[:300]})
    if r.status_code != 200:
        raise HTTPException(502, {"error": "brand node refused", "node_status": r.status_code})
    return r.json().get("rows", [])


@router.get("/blocked")
def blocked(weeks: int = Query(8, ge=1, le=26)):
    """Failed authenticity checks in the last `weeks` weeks (exact counts from the brand's verification API)."""
    now = config.current_week()
    week_from = max(1, now - weeks + 1)
    by_reason = _failures(["week", "reason_code"], week_from)
    by_store = _failures(["week", "store_id"], week_from)
    with db.connect("platform") as pc:
        names = {r["store_id"]: r["name"] for r in pc.execute("SELECT store_id, name FROM stores").fetchall()}
    week_list = list(range(week_from, now + 1))
    keep = set(week_list)
    by_reason = sorted(({"week": r["week"], "reason_code": r["reason_code"], "value": r["value"]}
                        for r in by_reason if r["week"] in keep), key=lambda r: (r["week"], r["reason_code"] or ""))
    by_store = sorted(({"week": r["week"], "store_id": r["store_id"], "value": r["value"]}
                       for r in by_store if r["week"] in keep), key=lambda r: (r["week"], r["store_id"] or ""))
    return {
        "brand_id": config.brand_id(),
        "current_week": now,
        "weeks": week_list,
        "total": sum(r["value"] for r in by_reason),
        "by_reason": by_reason,
        "by_store": by_store,
        "store_names": names,
        "exact": True,
        "source": "brand verification API (verification_failures), exact business counts",
    }
