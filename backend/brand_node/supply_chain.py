"""Brand's own supply chain data for the cockpit timeline (Bryntum). Exact business data, shown
only to the same brand. Owned by the cockpit work stream; router included in brand_node/main.py.

Shaped for a Bryntum Scheduler:
  resources     one row per actor: the brand, then distributors, then stores (with region)
  events        per batch: dispatch (brand row), held at distributor (distributor row),
                in channel at the store it was shipped to (store row), plus one highlighted
                event per (batch, store) where units sold at a store that is NOT a channel store
  dependencies  dispatch -> distributor (start_to_start: same week, next row), distributor -> store
                and distributor -> off-channel store (end_to_start)

Everything is aggregated per batch (counts); no serials are returned. Weeks are the seed's
integer week numbers; `end_week` is exclusive, so a one-week bar has end_week = start_week + 1.
"""
from fastapi import APIRouter, Depends, HTTPException

from backend import config, db
from backend.common.auth import require_node_token

router = APIRouter(prefix="/v1/supply-chain", tags=["supply-chain"])

_BATCHES = """
    SELECT b.batch_id, b.sku, b.distributor_id, b.shipped_week, cs.store_id, cs.week AS store_week,
           (SELECT COUNT(*) FROM serials s WHERE s.batch_id = b.batch_id) AS units,
           (SELECT COUNT(*) FROM serials s WHERE s.batch_id = b.batch_id AND s.sold_store_id = cs.store_id)
               AS sold_in_channel,
           (SELECT MAX(s.sold_week) FROM serials s WHERE s.batch_id = b.batch_id AND s.sold_store_id = cs.store_id)
               AS last_sold_week
    FROM batches b JOIN channel_shipments cs ON cs.batch_id = b.batch_id
    WHERE (%(sku)s::text IS NULL OR b.sku = %(sku)s)
    ORDER BY b.batch_id, cs.store_id
"""

# Units sold at a store that never received the batch through the brand's channel.
_OFF_CHANNEL = """
    SELECT s.batch_id, s.sold_store_id AS store_id, COUNT(*) AS units,
           MIN(s.sold_week) AS first_week, MAX(s.sold_week) AS last_week
    FROM serials s JOIN batches b ON b.batch_id = s.batch_id
    WHERE s.sold_store_id IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM channel_shipments c
                      WHERE c.batch_id = s.batch_id AND c.store_id = s.sold_store_id)
      AND (%(sku)s::text IS NULL OR b.sku = %(sku)s)
    GROUP BY s.batch_id, s.sold_store_id
    ORDER BY s.batch_id, s.sold_store_id
"""


def _partner_name(partners: dict, pid: str) -> str:
    return partners.get(pid, {}).get("name", pid)


@router.get("", dependencies=[Depends(require_node_token)])
def supply_chain(brand_id: str | None = None, sku: str | None = None, store_id: str | None = None):
    brand = config.brand_id()
    if brand_id is not None and brand_id != brand:
        raise HTTPException(403, {"refused": "WRONG_BRAND"})
    params = {"sku": sku or None}
    now = config.current_week()

    with db.connect("brand") as c:
        partner_rows = c.execute(
            "SELECT partner_id, type, name, region, city FROM partners ORDER BY type, partner_id").fetchall()
        batch_rows = c.execute(_BATCHES, params).fetchall()
        off_rows = c.execute(_OFF_CHANNEL, params).fetchall()

    partners = {p["partner_id"]: p for p in partner_rows}

    # store_id filter: batches shipped to that store, or with units that turned up there off-channel.
    if store_id:
        keep = {r["batch_id"] for r in batch_rows if r["store_id"] == store_id}
        keep |= {r["batch_id"] for r in off_rows if r["store_id"] == store_id}
        batch_rows = [r for r in batch_rows if r["batch_id"] in keep]
        off_rows = [r for r in off_rows if r["batch_id"] in keep]

    resources = [{"id": brand, "name": brand.capitalize(), "tier": "brand", "region": None, "city": None}]
    for tier in ("distributor", "store"):
        for p in partner_rows:
            if p["type"] == tier:
                resources.append({"id": p["partner_id"], "name": p["name"], "tier": tier,
                                  "region": p["region"], "city": p["city"]})

    events: list[dict] = []
    dependencies: list[dict] = []
    seen_batches: dict[str, dict] = {}
    for r in batch_rows:
        bid, dist = r["batch_id"], r["distributor_id"]
        if bid not in seen_batches:
            seen_batches[bid] = r
            events.append({
                "id": f"{bid}:dispatch", "resource_id": brand, "batch_id": bid, "sku": r["sku"],
                "kind": "dispatch", "name": f"{bid} to {_partner_name(partners, dist)}",
                "start_week": r["shipped_week"], "end_week": r["shipped_week"] + 1,
                "units": r["units"], "highlight": False,
            })
            events.append({
                "id": f"{bid}:dist", "resource_id": dist, "batch_id": bid, "sku": r["sku"],
                "kind": "distributor", "name": f"{bid} at {_partner_name(partners, dist)}",
                "start_week": r["shipped_week"],
                "end_week": max(r["store_week"], r["shipped_week"] + 1),
                "units": r["units"], "highlight": False,
            })
            dependencies.append({"id": f"{bid}:d1", "from": f"{bid}:dispatch", "to": f"{bid}:dist",
                                 "type": "start_to_start"})
        sid = r["store_id"]
        end = max((r["last_sold_week"] or now), r["store_week"]) + 1
        events.append({
            "id": f"{bid}:store:{sid}", "resource_id": sid, "batch_id": bid, "sku": r["sku"],
            "kind": "store", "name": f"{bid} at {_partner_name(partners, sid)}",
            "start_week": r["store_week"], "end_week": end,
            "units": r["units"], "sold": r["sold_in_channel"], "highlight": False,
        })
        dependencies.append({"id": f"{bid}:d2:{sid}", "from": f"{bid}:dist", "to": f"{bid}:store:{sid}",
                             "type": "end_to_start"})

    off_channel: list[dict] = []
    for r in off_rows:
        bid, sid = r["batch_id"], r["store_id"]
        b = seen_batches.get(bid)
        if b is None:
            continue
        channel_stores = sorted({x["store_id"] for x in batch_rows if x["batch_id"] == bid})
        events.append({
            "id": f"{bid}:off:{sid}", "resource_id": sid, "batch_id": bid, "sku": b["sku"],
            "kind": "off_channel",
            "name": f"{bid}: {r['units']} sold off-channel",
            "start_week": r["first_week"], "end_week": r["last_week"] + 1,
            "units": r["units"], "highlight": True,
        })
        dependencies.append({"id": f"{bid}:d3:{sid}", "from": f"{bid}:dist", "to": f"{bid}:off:{sid}",
                             "type": "end_to_start", "highlight": True})
        off_channel.append({
            "batch_id": bid, "sku": b["sku"], "distributor_id": b["distributor_id"],
            "channel_store_ids": channel_stores, "sold_store_id": sid, "units": r["units"],
            "first_week": r["first_week"], "last_week": r["last_week"],
        })

    weeks = [e["start_week"] for e in events] + [e["end_week"] for e in events]
    return {
        "brand_id": brand,
        "filters": {"sku": sku, "store_id": store_id},
        "current_week": now,
        "week_range": {"from": min(weeks, default=1), "to": max(weeks + [now + 1])},
        "resources": resources,
        "events": events,
        "dependencies": dependencies,
        "off_channel": off_channel,
        "totals": {
            "batches": len(seen_batches),
            "units": sum(b["units"] for b in seen_batches.values()),
            "off_channel_units": sum(o["units"] for o in off_channel),
        },
        "exact": True,
    }
