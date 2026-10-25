"""Build postman/trustledger.postman_collection.json (Postman Collection v2.1).

    uv run python scripts/build_postman.py

Two folders:
  1. Demo flow (platform API)   scan at Store A -> capture -> receipt; same serial at Store B -> blocked;
                                cases list and detail. Run it top to bottom on a freshly seeded stack.
  2. Brand verification API     the contract brands implement (POST /v1/verify, /confirm), with X-Node-Token.

Collection variables hold the base URLs and the token, so the same file works locally and on Render.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "postman" / "trustledger.postman_collection.json"


def _url(base_var: str, *segments: str) -> dict:
    path = [s for seg in segments for s in seg.strip("/").split("/") if s]
    return {"raw": "{{" + base_var + "}}/" + "/".join(path), "host": ["{{" + base_var + "}}"], "path": path}


def _tests(*lines: str) -> list[dict]:
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": list(lines)}}]


def request(name: str, method: str, base_var: str, path: str, body: dict | None = None,
            description: str = "", tests: list[str] | None = None) -> dict:
    req: dict = {"method": method, "header": [], "url": _url(base_var, path), "description": description}
    if body is not None:
        req["header"].append({"key": "Content-Type", "value": "application/json"})
        req["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2),
                       "options": {"raw": {"language": "json"}}}
    item = {"name": name, "request": req}
    if tests:
        item["event"] = _tests(*tests)
    return item


SCAN_BODY = {"store_id": "{{storeA}}", "serial": "{{serial}}", "sku": "{{sku}}", "amount": 899.0}

demo = {
    "name": "1. Demo flow (platform API)",
    "description": "The same-serial story. Run top to bottom against a freshly seeded stack "
                   "(`python -m backend.seed`), because a captured serial stays sold.",
    "item": [
        request("Health", "GET", "apiBaseUrl", "/health", tests=[
            "pm.test('api is up', () => pm.response.to.have.status(200));",
            "pm.collectionVariables.set('paypalMode', pm.response.json().paypal_mode);"]),
        request("Scan at Store A (verified, PayPal order created)", "POST", "apiBaseUrl", "/checkout/scan",
                SCAN_BODY,
                "Brand verifies X123 at Store A, so the platform creates a PayPal order with the verification "
                "id in custom_id.",
                tests=[
                    "const r = pm.response.json();",
                    "pm.test('200', () => pm.response.to.have.status(200));",
                    "pm.test('VERIFIED', () => pm.expect(r.status).to.eql('VERIFIED'));",
                    "pm.test('PayPal order exists', () => pm.expect(r.paypal_order_id).to.be.a('string'));",
                    "pm.collectionVariables.set('checkoutId', r.checkout_id);",
                    "pm.collectionVariables.set('paypalOrderId', r.paypal_order_id);",
                    "pm.collectionVariables.set('verificationId', r.verification_id);"]),
        request("Capture Store A payment", "POST", "apiBaseUrl", "/checkout/{{checkoutId}}/capture",
                description="Mock mode captures directly. In sandbox mode the buyer must approve the order "
                            "first (PayPal buttons in the web app), otherwise PayPal answers 422.",
                tests=[
                    "pm.test('200', () => pm.response.to.have.status(200));",
                    "pm.test('brand verified receipt', () => pm.expect(pm.response.json().brand_verified).to.eql(true));"]),
        request("Pay Store A with sandbox test card (alternative to Capture)", "POST", "apiBaseUrl",
                "/checkout/{{checkoutId}}/pay-test-card",
                description="Sandbox: use this INSTEAD of Capture. The server pays the existing order with a "
                            "PayPal sandbox test card and captures it, no buyer login. Run after Capture it answers "
                            "409 (already paid). Refused (403) in live mode.",
                tests=[
                    "pm.test('paid now or already paid', () => pm.expect(pm.response.code).to.be.oneOf([200, 409]));"]),
        request("Receipt", "GET", "apiBaseUrl", "/receipts/{{checkoutId}}", tests=[
            "const r = pm.response.json();",
            "pm.test('ids match', () => {",
            "  pm.expect(r.verification_id).to.eql(pm.collectionVariables.get('verificationId'));",
            "  pm.expect(r.paypal_order_id).to.eql(pm.collectionVariables.get('paypalOrderId'));",
            "});"]),
        request("Scan same serial at Store B (blocked, no PayPal order)", "POST", "apiBaseUrl", "/checkout/scan",
                SCAN_BODY | {"store_id": "{{storeB}}"},
                "Store B is not in X123's supply chain. No PayPal call is made and a case opens for the brand.",
                tests=[
                    "const r = pm.response.json();",
                    "pm.test('NOT_VERIFIED', () => pm.expect(r.status).to.eql('NOT_VERIFIED'));",
                    "pm.test('NOT_IN_CHANNEL', () => pm.expect(r.reason_code).to.eql('NOT_IN_CHANNEL'));",
                    "pm.test('no PayPal order', () => pm.expect(r.paypal_order_id).to.eql(null));",
                    "pm.collectionVariables.set('caseId', r.case_id);"]),
        request("List cases", "GET", "apiBaseUrl", "/cases", tests=[
            "const ids = pm.response.json().map(c => c.case_id);",
            "pm.test('Store B case listed', () => pm.expect(ids).to.include(pm.collectionVariables.get('caseId')));"]),
        request("Failed authenticity checks by week (cockpit chart)", "GET", "apiBaseUrl", "/cockpit/blocked",
                description="Exact counts of failed brand checks by week, reason and store, asked of the brand "
                            "node's aggregate API (no buyer data, no privacy budget).",
                tests=[
                    "const r = pm.response.json();",
                    "pm.test('exact brand counts', () => pm.expect(r.exact).to.eql(true));",
                    "pm.test('includes the Store B block', () => pm.expect(r.by_store.some(x => x.store_id === pm.collectionVariables.get('storeB'))).to.eql(true));"]),
        request("Case detail (agent steps)", "GET", "apiBaseUrl", "/cases/{{caseId}}",
                description="Re-send until status is `complete`; the worker fills in steps as it investigates.",
                tests=[
                    "const c = pm.response.json();",
                    "pm.test('case found', () => pm.expect(c.case_id).to.eql(pm.collectionVariables.get('caseId')));",
                    "console.log('case status', c.status, 'steps', c.steps.length);"]),
    ],
}

# Same as a verify, but with the folder's X-Node-Token auth switched off.
NO_TOKEN = request("Verify without token (401)", "POST", "brandBaseUrl", "/v1/verify",
                   {"serial": "{{serial}}", "sku": "{{sku}}", "store_id": "{{storeA}}"},
                   tests=["pm.test('401', () => pm.response.to.have.status(401));"])
NO_TOKEN["request"]["auth"] = {"type": "noauth"}

brand = {
    "name": "2. Brand verification API (contract)",
    "description": "What a brand implements (openapi/brand-verification.yaml). Calls go straight to the mock "
                   "brand node and need X-Node-Token. These calls do not create PayPal orders.",
    "auth": {"type": "apikey", "apikey": [
        {"key": "key", "value": "X-Node-Token", "type": "string"},
        {"key": "value", "value": "{{nodeToken}}", "type": "string"},
        {"key": "in", "value": "header", "type": "string"}]},
    "item": [
        request("Verify X123 at Store B (NOT_IN_CHANNEL)", "POST", "brandBaseUrl", "/v1/verify",
                {"serial": "{{serial}}", "sku": "{{sku}}", "store_id": "{{storeB}}",
                 "requested_at": "{{$isoTimestamp}}"},
                tests=[
                    "const r = pm.response.json();",
                    "pm.test('200', () => pm.response.to.have.status(200));",
                    "pm.test('NOT_VERIFIED / NOT_IN_CHANNEL', () => {",
                    "  pm.expect(r.result).to.eql('NOT_VERIFIED');",
                    "  pm.expect(r.reason_code).to.eql('NOT_IN_CHANNEL');",
                    "});"]),
        request("Verify X123 at Store A", "POST", "brandBaseUrl", "/v1/verify",
                {"serial": "{{serial}}", "sku": "{{sku}}", "store_id": "{{storeA}}",
                 "requested_at": "{{$isoTimestamp}}"},
                "VERIFIED on a fresh seed; ALREADY_SOLD once the demo flow captured X123.",
                tests=[
                    "const r = pm.response.json();",
                    "pm.test('200', () => pm.response.to.have.status(200));",
                    "pm.test('valid verdict', () => pm.expect(['VERIFIED', 'NOT_VERIFIED']).to.include(r.result));",
                    "pm.collectionVariables.set('brandVerificationId', r.verification_id);"]),
        request("Verify unknown serial", "POST", "brandBaseUrl", "/v1/verify",
                {"serial": "NOPE-0000", "sku": "{{sku}}", "store_id": "{{storeA}}"},
                tests=["pm.test('UNKNOWN_SERIAL', () => pm.expect(pm.response.json().reason_code).to.eql('UNKNOWN_SERIAL'));"]),
        NO_TOKEN,
        request("Confirm sale", "POST", "brandBaseUrl", "/v1/verify/{{brandVerificationId}}/confirm",
                {"paypal_order_id": "POSTMAN-TEST-ORDER", "captured_at": "{{$isoTimestamp}}"},
                "Marks the serial sold. 404 if the verification was not VERIFIED. Running this on a fresh seed "
                "marks X123 sold, so reseed before the demo flow.",
                tests=["pm.test('200 or 404', () => pm.expect([200, 404]).to.include(pm.response.code));"]),
    ],
}

collection = {
    "info": {
        "_postman_id": "8c3b6f0e-2d4a-4f5b-9e1c-7a2d5b6c9e01",
        "name": "TrustLedger",
        "description": "Product authenticity as a condition of PayPal payment. Generated by "
                       "scripts/build_postman.py; see postman/README.md.",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "item": [demo, brand],
    "variable": [
        {"key": "apiBaseUrl", "value": "http://localhost:8000", "type": "string"},
        {"key": "brandBaseUrl", "value": "http://localhost:8001", "type": "string"},
        {"key": "nodeToken", "value": "dev-token", "type": "string"},
        {"key": "serial", "value": "X123", "type": "string"},
        {"key": "sku", "value": "NMB-P8-128", "type": "string"},
        {"key": "storeA", "value": "store_a", "type": "string"},
        {"key": "storeB", "value": "store_b", "type": "string"},
        {"key": "checkoutId", "value": "", "type": "string"},
        {"key": "paypalOrderId", "value": "", "type": "string"},
        {"key": "verificationId", "value": "", "type": "string"},
        {"key": "caseId", "value": "", "type": "string"},
        {"key": "brandVerificationId", "value": "", "type": "string"},
        {"key": "paypalMode", "value": "", "type": "string"},
    ],
}


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(collection, indent=2) + "\n")
    n = sum(len(f["item"]) for f in collection["item"])
    print(f"wrote {OUT.relative_to(ROOT)} ({n} requests)")


if __name__ == "__main__":
    main()
