"""Platform API: checkout gate, receipts, PayPal webhooks, cases for the brand cockpit."""
import random
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from backend import config, db
from backend.api.paypal_client import PayPalError, CardPaymentUnavailable, paypal
from backend.common import http, notify
from backend.common.catalog import price_for
from backend.common.auth import require_node_token
from backend.api import cockpit, console, paypal_sdk, studio, supply_chain

app = FastAPI(title="TrustLedger API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=(config.env("CORS_ORIGINS", "http://localhost:3000")).split(","),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-TrustLedger-LLM", "X-TrustLedger-Model", "Retry-After"],
)
app.include_router(console.router)
app.include_router(paypal_sdk.router)
app.include_router(supply_chain.router)
app.include_router(cockpit.router)
app.include_router(studio.router)

REASON_TEXT = {
    "NOT_IN_CHANNEL": "This product is not in this store's supply chain.",
    "ALREADY_SOLD": "This product's serial has already been sold.",
    "UNKNOWN_SERIAL": "The brand doesn't recognize this serial.",
    "SKU_MISMATCH": "This serial belongs to a different product.",
    "IN_PROGRESS": "Another checkout for this unit is already in progress.",
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


@app.post("/checkout/scan")
def scan(req: ScanRequest):
    """Verify with the brand first. Only a VERIFIED product gets a PayPal order.
    The price comes from the server's catalog; any amount the client sends is ignored."""
    price = price_for(req.sku)
    if price is None:
        raise HTTPException(422, "unknown product")
    with http.client(config.brand_node_url()) as c:
        r = c.post("/v1/verify", json={"serial": req.serial, "sku": req.sku, "store_id": req.store_id})
        r.raise_for_status()
        v = r.json()

    checkout_id = f"chk_{uuid.uuid4().hex[:12]}"
    if v["result"] != "VERIFIED":
        with db.connect("platform") as pc, pc.transaction():
            pc.execute(INSERT_CHECKOUT, (checkout_id, req.store_id, req.serial, req.sku, price,
                                         v["verification_id"], None, "BLOCKED"))
            case_id, event = record_failure(pc, req, v)
        if event:
            notify.case_event(event, {"case_id": case_id, "store_id": req.store_id, "sku": req.sku,
                                      "reason_code": v["reason_code"]})
        return {"status": "NOT_VERIFIED", "checkout_id": checkout_id, "reason_code": v["reason_code"],
                "reason": REASON_TEXT.get(v["reason_code"], "Not verified by the brand."),
                "paypal_order_id": None, "case_id": case_id}

    for stale in _stale_captures(req.serial):
        _reconcile_stuck_capture(stale)
    if not _reserve(checkout_id, req, price, v["verification_id"]):
        # Refused before any order exists, so one unit can never have two live PayPal orders.
        return {"status": "NOT_VERIFIED", "checkout_id": checkout_id, "reason_code": "IN_PROGRESS",
                "reason": REASON_TEXT["IN_PROGRESS"], "paypal_order_id": None, "case_id": None}
    try:
        order = paypal.create_order(amount=price, sku=req.sku, name=PRODUCT_NAMES.get(req.sku, req.sku),
                                    custom_id=v["verification_id"], currency=config.env("PAYPAL_CURRENCY", "USD"))
    except Exception:
        _set_status(checkout_id, "FAILED")  # no order exists, so the unit is free again
        raise
    with db.connect("platform") as pc:
        pc.execute("UPDATE checkouts SET paypal_order_id=%s, status='AWAITING_PAYMENT' WHERE checkout_id=%s",
                   (order["id"], checkout_id))
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


PAYABLE = ("AWAITING_PAYMENT", "APPROVED")
# A unit is spoken for while a checkout holds it. Unpaid holds age out after HOLD_MINUTES; a capture in
# flight, a recorded-but-unfinished sale or a REVIEW hold never ages out.
RECENT_HOLD = ("RESERVING", "AWAITING_PAYMENT", "APPROVED")
ALWAYS_HELD = ("CAPTURING", "PAID_UNRECORDED", "REVIEW")
HOLD_MINUTES = 30
STUCK_CAPTURE_MINUTES = 2


def _reserve(checkout_id: str, req: "ScanRequest", price: float, verification_id: str) -> bool:
    """Hold the unit for this checkout, atomically. Refuse if another checkout holds it. Otherwise expire the
    older unpaid checkouts for this unit (their capture then returns 409) and insert this one with no order
    yet. The advisory lock serialises concurrent scans of the same serial."""
    with db.connect("platform") as pc, pc.transaction():
        pc.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (req.serial,))
        held = pc.execute(
            "SELECT 1 FROM checkouts WHERE serial=%s AND ("
            "status = ANY(%s) OR (status = ANY(%s) AND created_at > now() - make_interval(mins => %s))) LIMIT 1",
            (req.serial, list(ALWAYS_HELD), list(RECENT_HOLD), HOLD_MINUTES),
        ).fetchone()
        if held is not None:
            return False
        pc.execute("UPDATE checkouts SET status='EXPIRED' WHERE serial=%s AND status = ANY(%s)",
                   (req.serial, list(RECENT_HOLD)))
        pc.execute(INSERT_CHECKOUT, (checkout_id, req.store_id, req.serial, req.sku, price,
                                     verification_id, None, "RESERVING"))
    return True


def _stale_captures(serial: str) -> list[str]:
    with db.connect("platform") as pc:
        return [r["checkout_id"] for r in pc.execute(
            "SELECT checkout_id FROM checkouts WHERE serial=%s AND status='CAPTURING' "
            "AND claimed_at < now() - make_interval(mins => %s)", (serial, STUCK_CAPTURE_MINUTES)).fetchall()]


def _reconcile_stuck_capture(checkout_id: str) -> None:
    """A capture that died mid-way (process killed) leaves CAPTURING. Ask PayPal: if it captured, record the
    sale; if not, release the claim so the buyer can pay again."""
    with db.connect("platform") as pc:
        chk = pc.execute(
            "SELECT * FROM checkouts WHERE checkout_id=%s AND status='CAPTURING' "
            "AND claimed_at < now() - make_interval(mins => %s)", (checkout_id, STUCK_CAPTURE_MINUTES)).fetchone()
    if chk is None:
        return
    order = paypal.get_order(chk["paypal_order_id"])
    if order.get("status") == "COMPLETED":
        if _set_status(checkout_id, "PAID_UNRECORDED", from_status="CAPTURING"):
            _record_sale(checkout_id, chk, _payer_ref(order))
    else:
        _set_status(checkout_id, "AWAITING_PAYMENT", from_status="CAPTURING")


def _payable_checkout(checkout_id: str) -> dict | None:
    """The checkout row if it is VERIFIED, has a PayPal order and is still waiting for payment, else None.
    A BLOCKED checkout never has an order (paypal_order_id is NULL), so it can never be paid."""
    with db.connect("platform") as pc:
        chk = pc.execute("SELECT * FROM checkouts WHERE checkout_id=%s", (checkout_id,)).fetchone()
    if chk is None or chk["status"] not in PAYABLE or not chk["paypal_order_id"]:
        return None
    return chk


def _set_status(checkout_id: str, status: str, *, from_status: str | None = None) -> bool:
    """Set a checkout's status. With from_status, only if it still has that status (a compare-and-set)."""
    with db.connect("platform") as pc:
        if from_status is None:
            return pc.execute("UPDATE checkouts SET status=%s, claimed_at=NULL WHERE checkout_id=%s",
                              (status, checkout_id)).rowcount == 1
        return pc.execute(
            "UPDATE checkouts SET status=%s, claimed_at=CASE WHEN %s='CAPTURING' THEN now() END "
            "WHERE checkout_id=%s AND status=%s",
            (status, status, checkout_id, from_status)).rowcount == 1


def _record_sale(checkout_id: str, chk: dict, payer_ref: str) -> dict:
    """Second half of a payment, after PayPal has captured: confirm the sale with the brand, hand it to the
    PayPal-side node, mark CAPTURED. Each step is safe to repeat, so a failed record is retried, not re-captured."""
    with http.client(config.brand_node_url()) as c:
        r = c.post(f"/v1/verify/{chk['verification_id']}/confirm",
                   json={"paypal_order_id": chk["paypal_order_id"]})
    if r.status_code == 409:
        # PayPal has taken the money, but the brand's records say this unit sold to another order.
        _set_status(checkout_id, "REVIEW")
        raise HTTPException(409, "paid, but the brand's records show this unit sold to another order; flagged for review")
    r.raise_for_status()

    # Demographics are simulated (not in PayPal's public API). Seeded from the payer, so a retry gives the same row.
    rng = random.Random(payer_ref)
    with http.client(config.paypal_node_url()) as c:
        c.post("/v1/ingest", json={
            "order_id": chk["paypal_order_id"], "brand_id": config.brand_id(), "store_id": chk["store_id"],
            "sku": chk["sku"], "amount": chk["amount"], "payer_ref": payer_ref,
            "age_band": rng.choice(["18-24", "25-34", "35-44", "45-54", "55+"]),
            "gender": rng.choice(["female", "male", "other"]),
        }).raise_for_status()

    _set_status(checkout_id, "CAPTURED")
    return receipt(checkout_id)


def _payer_ref(order: dict) -> str:
    return (order.get("payer") or {}).get("payer_id", order.get("id", ""))


def _pay(checkout_id: str, chk: dict, pay) -> dict:
    """Run `pay(order_id)` (a capture, or the test-card confirm + capture) under a claim, so two requests
    can't pay one order. A PayPal refusal releases the claim. A transport error releases it too: PayPal keys
    the capture by `capture-<order id>`, so a retry returns the stored result instead of charging twice."""
    prior = chk["status"]
    if not _set_status(checkout_id, "CAPTURING", from_status=prior):
        raise HTTPException(409, "this checkout is already being paid")
    try:
        result = pay(chk["paypal_order_id"])
    except CardPaymentUnavailable as e:
        _set_status(checkout_id, prior, from_status="CAPTURING")
        raise HTTPException(503, str(e))
    except PayPalError as e:
        # e.g. 422 ORDER_NOT_APPROVED when the buyer hasn't approved yet. Pass PayPal's reason through.
        _set_status(checkout_id, prior, from_status="CAPTURING")
        body = e.body
        issue = ((body.get("details") or [{}])[0]).get("issue") or body.get("name") or "PAYPAL_ERROR"
        code = 409 if e.status_code == 422 else 502
        raise HTTPException(code, {"paypal_issue": issue, "message": body.get("message", str(e))})
    except Exception:
        # Outcome unknown: PayPal may have captured. Keep the claim; _reconcile_stuck_capture settles it.
        raise HTTPException(502, "payment status unknown; it will be checked with PayPal, do not pay again")
    if result.get("status") != "COMPLETED":
        # Not captured (e.g. PENDING): keep the claim, the reconcile step decides once PayPal's status is final.
        raise HTTPException(502, {"paypal_status": result.get("status")})

    # PayPal has the money. Mark it paid-but-unrecorded, so a failure below is retried by recording, not capturing.
    _set_status(checkout_id, "PAID_UNRECORDED", from_status="CAPTURING")
    try:
        return _record_sale(checkout_id, chk, _payer_ref(result))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "paid with PayPal; recording the sale failed. Retry the capture to finish.")


@app.post("/checkout/{checkout_id}/capture")
def capture(checkout_id: str):
    _reconcile_stuck_capture(checkout_id)
    chk = _payable_checkout(checkout_id)
    if chk is not None:
        return _pay(checkout_id, chk, paypal.capture_order)
    with db.connect("platform") as pc:
        chk = pc.execute("SELECT * FROM checkouts WHERE checkout_id=%s", (checkout_id,)).fetchone()
    if chk is not None and chk["status"] == "PAID_UNRECORDED":
        # PayPal already has the money; finish recording it. Nothing is captured twice.
        order = paypal.get_order(chk["paypal_order_id"])
        if order.get("status") != "COMPLETED":
            raise HTTPException(409, "PayPal does not show this order as captured")
        return _record_sale(checkout_id, chk, _payer_ref(order))
    raise HTTPException(409, "checkout is not awaiting payment")


@app.post("/checkout/{checkout_id}/release")
def release(checkout_id: str):
    """Clerk releases a held unit whose buyer walked away. Only before a capture starts; a later capture of
    this checkout returns 409 because its status is no longer payable."""
    with db.connect("platform") as pc:
        n = pc.execute("UPDATE checkouts SET status='RELEASED' WHERE checkout_id=%s AND status = ANY(%s)",
                       (checkout_id, list(PAYABLE))).rowcount
    if n == 0:
        raise HTTPException(409, "checkout is not holding a unit")
    return {"status": "RELEASED", "checkout_id": checkout_id}


@app.post("/checkout/{checkout_id}/pay-test-card")
def pay_test_card(checkout_id: str):
    """One-click sandbox payment: a PayPal sandbox test card pays the order made after VERIFIED, then the
    normal capture path runs. Refused in live mode. Unknown checkout: 404. Blocked or already paid: 409."""
    if paypal.mode not in ("sandbox", "mock"):
        raise HTTPException(403, "test-card payments are sandbox only")
    with db.connect("platform") as pc:
        exists = pc.execute("SELECT 1 FROM checkouts WHERE checkout_id=%s", (checkout_id,)).fetchone()
    if exists is None:
        raise HTTPException(404, "unknown checkout")
    chk = _payable_checkout(checkout_id)
    if chk is None:
        raise HTTPException(409, "checkout is not awaiting payment (blocked checkouts have no PayPal order)")
    try:
        return _pay(checkout_id, chk, paypal.pay_with_test_card)
    except CardPaymentUnavailable as e:
        raise HTTPException(503, str(e))


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


def _settle_from_webhook(order_id: str) -> int:
    """Record a capture that finished outside /capture, through the same path as /capture, after PayPal's own
    order status says COMPLETED. A capture still in flight in /capture is left to that request."""
    with db.connect("platform") as pc:
        chk = pc.execute("SELECT * FROM checkouts WHERE paypal_order_id=%s", (order_id,)).fetchone()
    if chk is None:
        return 0
    _reconcile_stuck_capture(chk["checkout_id"])
    with db.connect("platform") as pc:
        chk = pc.execute("SELECT * FROM checkouts WHERE paypal_order_id=%s", (order_id,)).fetchone()
    if chk["status"] == "CAPTURING":
        raise HTTPException(503, "capture in progress; PayPal should redeliver")
    if chk["status"] not in ("AWAITING_PAYMENT", "APPROVED", "PAID_UNRECORDED"):
        return 0
    order = paypal.get_order(order_id)
    if order.get("status") != "COMPLETED":
        return 0
    if chk["status"] != "PAID_UNRECORDED" and not _set_status(
            chk["checkout_id"], "PAID_UNRECORDED", from_status=chk["status"]):
        return 0
    try:
        _record_sale(chk["checkout_id"], chk, _payer_ref(order))  # a transient failure raises, so PayPal redelivers
    except HTTPException:
        return 0  # the brand refused the sale: _record_sale has set REVIEW, and redelivery won't change that
    return 1


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
        # Normally /capture records the sale; this covers a capture finished outside our endpoint.
        updated = _settle_from_webhook(order_id)
    # Future extension: CUSTOMER.DISPUTE.CREATED -> look up custom_id -> provide evidence via Disputes API.
    return {"received": kind, "order_id": order_id, "updated": updated}


# ---------------------------------------------------------------- cases (cockpit)

@app.get("/cases")
def list_cases():
    with db.connect("platform") as pc:
        return pc.execute(
            """SELECT c.*,
                      (SELECT COUNT(*) FROM case_steps s 
                       WHERE s.case_id=c.case_id 
                         AND s.kind='finding' 
                         AND COALESCE(s.run, 1) = GREATEST(COALESCE(c.run_count, 1), 1)) AS findings,
                      (SELECT COUNT(*) FROM case_steps s 
                       WHERE s.case_id=c.case_id 
                         AND COALESCE(s.run, 1) = GREATEST(COALESCE(c.run_count, 1), 1)) AS step_count
               FROM cases c ORDER BY created_at DESC"""
        ).fetchall()


@app.get("/cases/{case_id}")
def get_case(case_id: str, run: int | None = None, include_earlier_steps: bool = False):
    with db.connect("platform") as pc:
        case = pc.execute("SELECT * FROM cases WHERE case_id=%s", (case_id,)).fetchone()
        if case is None:
            raise HTTPException(404)
        all_steps = pc.execute("SELECT * FROM case_steps WHERE case_id=%s ORDER BY n", (case_id,)).fetchall()

    runs_in_steps = {s.get("run") or 1 for s in all_steps}
    latest_run = case.get("run_count") or (max(runs_in_steps) if runs_in_steps else 1)
    target_run = run if run is not None else latest_run

    earlier_runs = []
    earlier_run_numbers = sorted(r for r in runs_in_steps if r < latest_run)
    for r_num in earlier_run_numbers:
        r_steps = [s for s in all_steps if (s.get("run") or 1) == r_num]
        entry = {"run": r_num, "step_count": len(r_steps)}
        if include_earlier_steps:
            entry["steps"] = r_steps
        earlier_runs.append(entry)

    selected_steps = [s for s in all_steps if (s.get("run") or 1) == target_run]
    return {**case, "steps": selected_steps, "earlier_runs": earlier_runs}


# ---------------------------------------------------------------- internal (worker)

class StepIn(BaseModel):
    kind: str          # thought | tool_call | tool_result | finding
    payload: dict
    run: int | None = None


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
        run = step.run
        if run is None:
            c = pc.execute("SELECT run_count FROM cases WHERE case_id=%s", (case_id,)).fetchone()
            run = (c["run_count"] if c and c.get("run_count") else 1)
        n = pc.execute("SELECT COALESCE(MAX(n), 0) + 1 AS n FROM case_steps WHERE case_id=%s", (case_id,)).fetchone()["n"]
        step_id = f"{case_id}:s{n}"
        pc.execute("INSERT INTO case_steps (step_id, case_id, n, run, kind, payload) VALUES (%s,%s,%s,%s,%s,%s)",
                   (step_id, case_id, n, run, step.kind, Jsonb(step.payload)))
    return {"step_id": step_id, "n": n, "run": run}


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
