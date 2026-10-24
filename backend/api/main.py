"""Platform API: checkout gate, receipts, PayPal webhooks, cases for the brand cockpit."""
import random
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from backend import config, db
from backend.api.paypal_client import PayPalError, paypal
from backend.common import http, notify
from backend.common.auth import require_node_token
from backend.api import cockpit, console, paypal_sdk, supply_chain

app = FastAPI(title="TrustLedger API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=(config.env("CORS_ORIGINS", "http://localhost:3000")).split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(console.router)
app.include_router(paypal_sdk.router)
app.include_router(supply_chain.router)
app.include_router(cockpit.router)

REASON_TEXT = {
    "NOT_IN_CHANNEL": "This product is not in this store's supply chain.",
    "ALREADY_SOLD": "This product's serial has already been sold.",
    "UNKNOWN_SERIAL": "The brand doesn't recognize this serial.",
    "SKU_MISMATCH": "This serial belongs to a different product.",
}
INSERT_CHECKOUT = (
    "INSERT INTO checkouts (checkout_id, store_id, serial, sku, amount, verification_id, paypal_order_id, status) "
    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
)
PRODUCT_NAMES = {"NMB-P8-128": "Nimbus P8 128GB", "NMB-P8-256": "Nimbus P8 256GB", "NMB-A5-64": "Nimbus A5 64GB"}


@app.get("/health")
def health():
    return {"ok": True, "paypal_mode": paypal.mode}


@app.get("/stores")
def stores():
    with db.connect("platform") as c:
        return c.execute("SELECT * FROM stores ORDER BY store_id").fetchall()


@app.get("/demo/serial")
def demo_serial(store_id: str):
    """Demo only: an unsold demo serial (and its product) at this store, from the brand node."""
    with http.client(config.brand_node_url()) as c:
        r = c.get("/v1/demo/serial", params={"store_id": store_id})
    if r.status_code == 404:
        raise HTTPException(404, r.json().get("detail", "no demo stock"))
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------- checkout gate

class ScanRequest(BaseModel):
    store_id: str
    serial: str
    sku: str
    amount: float


@app.post("/checkout/scan")
def scan(req: ScanRequest):
    """Verify with the brand first. Only a VERIFIED product gets a PayPal order."""
    with http.client(config.brand_node_url()) as c:
        r = c.post("/v1/verify", json={"serial": req.serial, "sku": req.sku, "store_id": req.store_id})
        r.raise_for_status()
        v = r.json()

    checkout_id = f"chk_{uuid.uuid4().hex[:12]}"
    if v["result"] != "VERIFIED":
        with db.connect("platform") as pc, pc.transaction():
            pc.execute(INSERT_CHECKOUT, (checkout_id, req.store_id, req.serial, req.sku, req.amount,
                                         v["verification_id"], None, "BLOCKED"))
            case_id, event = record_failure(pc, req, v)
        if event:
            notify.case_event(event, {"case_id": case_id, "store_id": req.store_id, "sku": req.sku,
                                      "reason_code": v["reason_code"]})
        return {"status": "NOT_VERIFIED", "checkout_id": checkout_id, "reason_code": v["reason_code"],
                "reason": REASON_TEXT.get(v["reason_code"], "Not verified by the brand."),
                "paypal_order_id": None, "case_id": case_id}

    order = paypal.create_order(amount=req.amount, sku=req.sku, name=PRODUCT_NAMES.get(req.sku, req.sku),
                                custom_id=v["verification_id"])
    with db.connect("platform") as pc:
        pc.execute(INSERT_CHECKOUT, (checkout_id, req.store_id, req.serial, req.sku, req.amount,
                                     v["verification_id"], order["id"], "AWAITING_PAYMENT"))
    return {"status": "VERIFIED", "checkout_id": checkout_id, "verification_id": v["verification_id"],
            "paypal_order_id": order["id"], "paypal_mode": paypal.mode}


def material_change(case: dict) -> bool:
    """Re-run the agent only when the problem grew: failures doubled or a new SKU appeared."""
    return (case["failure_count"] >= 2 * max(case["run_failure_count"], 1)
            or not set(case["skus"]) <= set(case["run_skus"]))


def record_failure(pc, req: "ScanRequest", v: dict) -> tuple[str, str | None]:
    """A case is one open problem (brand, store, reason), not one failed scan.

    Attach the failure to the matching open case, or open a new one. Returns (case_id, notify event or None).
    """
    case = pc.execute(
        "SELECT * FROM cases WHERE brand_id=%s AND store_id=%s AND reason_code=%s AND status <> 'closed' "
        "ORDER BY created_at DESC LIMIT 1 FOR UPDATE",
        (config.brand_id(), req.store_id, v["reason_code"]),
    ).fetchone()
    if case is None:
        case_id = f"case_{uuid.uuid4().hex[:10]}"
        pc.execute(
            "INSERT INTO cases (case_id, brand_id, verification_id, store_id, sku, serial, reason_code, status, skus) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,'open',%s)",
            (case_id, config.brand_id(), v["verification_id"], req.store_id, req.sku, req.serial,
             v["reason_code"], [req.sku]))
        event = "case_opened"
    else:
        case_id = case["case_id"]
        case = pc.execute(
            "UPDATE cases SET failure_count = failure_count + 1, updated_at = now(), "
            "skus = CASE WHEN %s = ANY(skus) THEN skus ELSE array_append(skus, %s) END "
            "WHERE case_id=%s RETURNING *", (req.sku, req.sku, case_id)).fetchone()
        event = None
        # A running investigation re-checks this when it finishes; a finished one is re-queued here.
        if case["status"] in ("complete", "failed") and material_change(case):
            pc.execute("UPDATE cases SET status='open' WHERE case_id=%s", (case_id,))
            event = "case_reopened"
    pc.execute("INSERT INTO case_failures (verification_id, case_id, serial, sku) VALUES (%s,%s,%s,%s)",
               (v["verification_id"], case_id, req.serial, req.sku))
    return case_id, event


@app.post("/checkout/{checkout_id}/capture")
def capture(checkout_id: str):
    with db.connect("platform") as pc:
        chk = pc.execute("SELECT * FROM checkouts WHERE checkout_id=%s", (checkout_id,)).fetchone()
    if chk is None or chk["status"] not in ("AWAITING_PAYMENT", "APPROVED"):
        raise HTTPException(409, "checkout is not awaiting payment")
    try:
        result = paypal.capture_order(chk["paypal_order_id"])
    except PayPalError as e:
        # e.g. 422 ORDER_NOT_APPROVED when the buyer hasn't approved yet. Pass PayPal's reason through.
        body = e.body
        issue = ((body.get("details") or [{}])[0]).get("issue") or body.get("name") or "PAYPAL_ERROR"
        code = 409 if e.status_code == 422 else 502
        raise HTTPException(code, {"paypal_issue": issue, "message": body.get("message", str(e))})
    if result.get("status") != "COMPLETED":
        raise HTTPException(502, {"paypal_status": result.get("status")})

    with http.client(config.brand_node_url()) as c:
        c.post(f"/v1/verify/{chk['verification_id']}/confirm",
               json={"paypal_order_id": chk["paypal_order_id"]}).raise_for_status()

    # Hand the sale to the PayPal-side node. Demographics are simulated (not in PayPal's public API).
    payer_ref = (result.get("payer") or {}).get("payer_id", chk["paypal_order_id"])
    rng = random.Random(payer_ref)
    with http.client(config.paypal_node_url()) as c:
        c.post("/v1/ingest", json={
            "order_id": chk["paypal_order_id"], "brand_id": config.brand_id(), "store_id": chk["store_id"],
            "sku": chk["sku"], "amount": chk["amount"], "payer_ref": payer_ref,
            "age_band": rng.choice(["18-24", "25-34", "35-44", "45-54", "55+"]),
            "gender": rng.choice(["female", "male", "other"]),
        }).raise_for_status()

    with db.connect("platform") as pc:
        pc.execute("UPDATE checkouts SET status='CAPTURED' WHERE checkout_id=%s", (checkout_id,))
    return receipt(checkout_id)


@app.get("/receipts/{checkout_id}")
def receipt(checkout_id: str):
    with db.connect("platform") as pc:
        r = pc.execute(
            "SELECT c.*, s.name AS store_name FROM checkouts c JOIN stores s USING (store_id) WHERE checkout_id=%s",
            (checkout_id,),
        ).fetchone()
    if r is None:
        raise HTTPException(404)
    return {**r, "product": PRODUCT_NAMES.get(r["sku"], r["sku"]),
            "brand_verified": r["status"] == "CAPTURED"}


@app.post("/paypal/webhooks")
async def webhooks(request: Request):
    event = await request.json()
    headers = {k.lower(): v for k, v in request.headers.items()}
    if not paypal.verify_webhook(headers, event):
        raise HTTPException(400, "signature verification failed")
    kind = event.get("event_type")
    resource = event.get("resource") or {}
    # PAYMENT.CAPTURE.* resources carry the order id here; CHECKOUT.ORDER.* resources are the order itself.
    order_id = ((resource.get("supplementary_data") or {}).get("related_ids") or {}).get("order_id") \
        or resource.get("id")
    updated = 0
    if kind == "CHECKOUT.ORDER.APPROVED" and order_id:
        with db.connect("platform") as pc:
            updated = pc.execute("UPDATE checkouts SET status='APPROVED' WHERE paypal_order_id=%s "
                                 "AND status='AWAITING_PAYMENT'", (order_id,)).rowcount
    elif kind == "PAYMENT.CAPTURE.COMPLETED" and order_id:
        # Normally /capture already set CAPTURED; this covers a capture finished outside our endpoint.
        with db.connect("platform") as pc:
            updated = pc.execute("UPDATE checkouts SET status='CAPTURED' WHERE paypal_order_id=%s "
                                 "AND status IN ('AWAITING_PAYMENT','APPROVED')", (order_id,)).rowcount
    # Future extension: CUSTOMER.DISPUTE.CREATED -> look up custom_id -> provide evidence via Disputes API.
    return {"received": kind, "order_id": order_id, "updated": updated}


# ---------------------------------------------------------------- cases (cockpit)

@app.get("/cases")
def list_cases():
    with db.connect("platform") as pc:
        return pc.execute(
            """SELECT c.*,
                      (SELECT COUNT(*) FROM case_steps s WHERE s.case_id=c.case_id AND s.kind='finding') AS findings,
                      (SELECT COUNT(*) FROM case_steps s WHERE s.case_id=c.case_id) AS step_count
               FROM cases c ORDER BY created_at DESC"""
        ).fetchall()


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    with db.connect("platform") as pc:
        case = pc.execute("SELECT * FROM cases WHERE case_id=%s", (case_id,)).fetchone()
        if case is None:
            raise HTTPException(404)
        steps = pc.execute("SELECT * FROM case_steps WHERE case_id=%s ORDER BY n", (case_id,)).fetchall()
    return {**case, "steps": steps}


# ---------------------------------------------------------------- internal (worker)

class StepIn(BaseModel):
    kind: str          # thought | tool_call | tool_result | finding
    payload: dict


class FinishIn(BaseModel):
    status: str        # complete | failed | waiting_capacity
    summary: str
    confidence: str | None = None  # low | medium | high, from the agent
    agent_mode: str = "live"       # live | replay
    agent_model: str | None = None
    agent_reason: str | None = None
    source_case_id: str | None = None
    replay_recorded_at: str | None = None


@app.post("/internal/cases/claim", dependencies=[Depends(require_node_token)])
def claim_case():
    # SKIP LOCKED lets several workers claim cases without taking the same one.
    with db.connect("platform") as pc:
        row = pc.execute(
            """UPDATE cases SET status='investigating', run_count = run_count + 1,
                   run_failure_count = failure_count, run_skus = skus
               WHERE case_id = (SELECT case_id FROM cases
                                WHERE status = 'open' OR (status = 'waiting_capacity' AND (retry_after IS NULL OR retry_after <= now()))
                                ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED)
               RETURNING *"""
        ).fetchone()
    return {"case": row}


@app.post("/internal/cases/{case_id}/steps", dependencies=[Depends(require_node_token)])
def add_step(case_id: str, step: StepIn):
    with db.connect("platform") as pc, pc.transaction():
        n = pc.execute("SELECT COALESCE(MAX(n), 0) + 1 AS n FROM case_steps WHERE case_id=%s", (case_id,)).fetchone()["n"]
        step_id = f"{case_id}:s{n}"
        pc.execute("INSERT INTO case_steps (step_id, case_id, n, kind, payload) VALUES (%s,%s,%s,%s,%s)",
                   (step_id, case_id, n, step.kind, Jsonb(step.payload)))
    return {"step_id": step_id, "n": n}


@app.post("/internal/cases/{case_id}/finish", dependencies=[Depends(require_node_token)])
def finish_case(case_id: str, body: FinishIn):
    with db.connect("platform") as pc:
        case = pc.execute(
            """UPDATE cases SET status=%s, summary=%s, confidence=%s, agent_mode=%s, agent_model=%s,
                   agent_reason=%s, source_case_id=%s, replay_recorded_at=%s,
                   retry_after=(CASE WHEN %s = 'waiting_capacity' THEN now() + interval '15 minutes' ELSE NULL END),
                   updated_at=now()
               WHERE case_id=%s RETURNING *""",
            (body.status, body.summary, body.confidence, body.agent_mode, body.agent_model,
             body.agent_reason, body.source_case_id, body.replay_recorded_at, body.status, case_id)
        ).fetchone()
        # Failures that arrived during the run may have grown the problem enough to warrant another run.
        if case and body.status == "complete" and material_change(case):
            pc.execute("UPDATE cases SET status='open' WHERE case_id=%s", (case_id,))
    if case:
        if body.status == "complete":
            event_type = "case_completed"
        elif body.status == "waiting_capacity":
            event_type = "case_deferred"
        else:
            event_type = "case_failed"
        notify.case_event(event_type, case, body.summary)
    return {"ok": True}
