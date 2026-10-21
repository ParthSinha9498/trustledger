"""Mock brand system: the verification API brands implement, plus brand-side aggregate queries.

How a brand decides VERIFIED / NOT_VERIFIED is its own internal logic. This mock checks
its serial registry and supply chain records. Brand-side data is about businesses
(serials, shipments, stores), so queries return exact aggregates, never rows.
"""
import uuid

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from backend import config, db
from backend.common.auth import require_node_token
from backend.common.query_spec import MAX_CELLS, QuerySpec, SpecRefused, validate_for_node

app = FastAPI(title="TrustLedger brand node (mock brand)")

from backend.brand_node import supply_chain  # noqa: E402

app.include_router(supply_chain.router)


# ---------------------------------------------------------------- verification API

class VerifyRequest(BaseModel):
    serial: str
    sku: str
    store_id: str


class VerifyResponse(BaseModel):
    verification_id: str
    result: str                    # VERIFIED | NOT_VERIFIED
    reason_code: str | None = None  # NOT_IN_CHANNEL | ALREADY_SOLD | UNKNOWN_SERIAL | SKU_MISMATCH


class ConfirmRequest(BaseModel):
    paypal_order_id: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/verify", response_model=VerifyResponse, dependencies=[Depends(require_node_token)])
def verify(req: VerifyRequest) -> VerifyResponse:
    with db.connect("brand") as c:
        row = c.execute(
            """SELECT s.serial, s.sku, s.sold_store_id, cs.store_id AS channel_store
               FROM serials s LEFT JOIN channel_shipments cs ON cs.batch_id = s.batch_id
               WHERE s.serial = %s""",
            (req.serial,),
        ).fetchone()
    if row is None:
        result, reason = "NOT_VERIFIED", "UNKNOWN_SERIAL"
    elif row["sku"] != req.sku:
        result, reason = "NOT_VERIFIED", "SKU_MISMATCH"
    elif row["channel_store"] != req.store_id:
        # Checked before "already sold": a clone at the wrong store fails on its first attempt,
        # even if the genuine unit hasn't sold yet.
        result, reason = "NOT_VERIFIED", "NOT_IN_CHANNEL"
    elif row["sold_store_id"] is not None:
        result, reason = "NOT_VERIFIED", "ALREADY_SOLD"
    else:
        result, reason = "VERIFIED", None
    vid = f"ver_{uuid.uuid4().hex[:12]}"
    with db.connect("brand") as c:
        c.execute(
            "INSERT INTO verification_log (verification_id, serial, sku, store_id, result, reason_code, week) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (vid, req.serial, req.sku, req.store_id, result, reason, config.current_week()),
        )
    return VerifyResponse(verification_id=vid, result=result, reason_code=reason)


@app.post("/v1/verify/{verification_id}/confirm", dependencies=[Depends(require_node_token)])
def confirm(verification_id: str, req: ConfirmRequest):
    """Called after PayPal capture: the brand marks the serial sold."""
    with db.connect("brand") as c:
        v = c.execute("SELECT * FROM verification_log WHERE verification_id=%s", (verification_id,)).fetchone()
        if v is None or v["result"] != "VERIFIED":
            raise HTTPException(404, "no verified check with that id")
        c.execute(
            "UPDATE serials SET sold_store_id=%s, sold_week=%s, sold_order_id=%s "
            "WHERE serial=%s AND sold_store_id IS NULL",
            (v["store_id"], config.current_week(), req.paypal_order_id, v["serial"]),
        )
    return {"ok": True}


# ---------------------------------------------------------------- aggregate queries

_BASE = {
    "shipped_units": """
        SELECT cs.store_id, p.region, p.city, s.sku, cs.week AS week, cs.distributor_id, NULL AS reason_code
        FROM serials s JOIN channel_shipments cs ON cs.batch_id = s.batch_id
        JOIN partners p ON p.partner_id = cs.store_id""",
    "sold_units": """
        SELECT s.sold_store_id AS store_id, p.region, p.city, s.sku, s.sold_week AS week,
               cs.distributor_id, NULL AS reason_code
        FROM serials s JOIN partners p ON p.partner_id = s.sold_store_id
        LEFT JOIN channel_shipments cs ON cs.batch_id = s.batch_id
        WHERE s.sold_store_id IS NOT NULL""",
    "verification_failures": """
        SELECT v.store_id, p.region, p.city, v.sku, v.week, cs.distributor_id, v.reason_code
        FROM verification_log v JOIN partners p ON p.partner_id = v.store_id
        LEFT JOIN serials s ON s.serial = v.serial
        LEFT JOIN channel_shipments cs ON cs.batch_id = s.batch_id
        WHERE v.result = 'NOT_VERIFIED'""",
}


class QueryRequest(BaseModel):
    brand_id: str
    spec: QuerySpec
    purpose: str = "console"


@app.post("/v1/query", dependencies=[Depends(require_node_token)])
def query(req: QueryRequest):
    if req.brand_id != config.brand_id():
        raise HTTPException(403, {"refused": "WRONG_BRAND"})
    try:
        validate_for_node(req.spec, "brand")
    except SpecRefused as e:
        raise HTTPException(403, {"refused": e.code, "detail": e.detail})

    spec = req.spec
    where, params = [], []
    f = spec.filters
    for col, values in (("sku", f.sku), ("region", f.region), ("store_id", f.store_id)):
        if values:
            where.append(f"{col} = ANY(%s)")
            params.append(values)
    if f.week_from:
        where.append("week >= %s"); params.append(f.week_from)
    if f.week_to:
        where.append("week <= %s"); params.append(f.week_to)

    dims = list(spec.group_by)  # validated against a whitelist, safe to interpolate
    select = ", ".join(dims + ["COUNT(*) AS value"])
    sql = f"SELECT {select} FROM ({_BASE[spec.metric]}) base"
    if where:
        sql += " WHERE " + " AND ".join(where)
    if dims:
        sql += f" GROUP BY {', '.join(dims)} ORDER BY value DESC"
    with db.connect("brand") as c:
        rows = [dict(r) for r in c.execute(sql, params).fetchall()]
    if len(rows) > MAX_CELLS:
        raise HTTPException(403, {"refused": "TOO_MANY_CELLS"})
    return {"node": "brand", "metric": spec.metric, "group_by": dims, "rows": rows, "exact": True}
