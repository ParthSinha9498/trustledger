"""Export TrustLedger's OpenAPI specs from the FastAPI apps.

    uv run python scripts/export_openapi.py           # write openapi/*.yaml
    uv run python scripts/export_openapi.py --check   # exit 1 if the committed specs are stale

Writes
  openapi/brand-verification.yaml   the contract brands implement (POST /v1/verify, POST /v1/verify/{id}/confirm).
                                    This is the file to import into APIMatic (SDKs, docs portal) and Postman.
  openapi/platform.yaml             the api service (checkout gate, receipts, cases, console, ...)

Schemas and paths come from the running code (FastAPI's app.openapi()); this script only adds the
contract wording, examples, enums and the X-Node-Token security scheme. If PyYAML is missing the
specs are written as .json instead.
"""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PAYPAL_MODE", "mock")  # importing the api must never need PayPal keys
os.environ.setdefault("LLM_MODE", "mock")

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

OUT = ROOT / "openapi"
VERSION = "1.0.0"

NODE_TOKEN_SCHEME = {
    "NodeToken": {
        "type": "apiKey",
        "in": "header",
        "name": "X-Node-Token",
        "description": "Shared secret issued to the checkout platform. Every call must carry it; a missing "
                       "or wrong token gets 401.",
    }
}
ERROR_SCHEMA = {
    "type": "object",
    "properties": {"detail": {"description": "Human-readable error.", "type": "string"}},
    "required": ["detail"],
    "example": {"detail": "bad node token"},
}
REASON_CODES = ["NOT_IN_CHANNEL", "ALREADY_SOLD", "UNKNOWN_SERIAL", "SKU_MISMATCH"]


def _strip_token_header(op: dict) -> None:
    """FastAPI renders the auth dependency as a header parameter; publish it as a security scheme."""
    op["parameters"] = [p for p in op.get("parameters", [])
                        if not (p.get("in") == "header" and p.get("name", "").lower() == "x-node-token")]
    if not op["parameters"]:
        del op["parameters"]


def _collect_refs(node, found: set[str]) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            found.add(ref.rsplit("/", 1)[1])
        for v in node.values():
            _collect_refs(v, found)
    elif isinstance(node, list):
        for v in node:
            _collect_refs(v, found)


def _prune_schemas(spec: dict) -> None:
    schemas = spec["components"]["schemas"]
    keep: set[str] = set()
    _collect_refs(spec["paths"], keep)
    while True:
        more: set[str] = set()
        for name in keep:
            _collect_refs(schemas.get(name, {}), more)
        if more <= keep:
            break
        keep |= more
    spec["components"]["schemas"] = {k: schemas[k] for k in sorted(keep) if k in schemas}


# --------------------------------------------------------------------------- brand verification

def brand_verification_spec() -> dict:
    from backend.brand_node.main import app

    gen = app.openapi()
    paths = {p: copy.deepcopy(gen["paths"][p]) for p in ("/v1/verify", "/v1/verify/{verification_id}/confirm")}
    schemas = copy.deepcopy(gen["components"]["schemas"])

    # The code is the source of truth for field names; fail loudly if it drifts from the contract.
    for name, fields in {"VerifyRequest": {"serial", "sku", "store_id"},
                         "VerifyResponse": {"verification_id", "result", "reason_code"},
                         "ConfirmRequest": {"paypal_order_id"}}.items():
        missing = fields - set(schemas[name]["properties"])
        if missing:
            raise SystemExit(f"{name} lost contract fields {missing}; update the contract deliberately")

    vreq = schemas["VerifyRequest"]
    vreq["description"] = "One product at one store, checked before any payment is created."
    vreq["properties"]["serial"].update(description="Serial number scanned from the product.", example="X123")
    vreq["properties"]["sku"].update(description="The brand's SKU for the product being sold.",
                                     example="NMB-P8-128")
    vreq["properties"]["store_id"].update(
        description="The selling store, as the brand knows it from its own channel records.", example="store_a")
    vreq["properties"].setdefault("requested_at", {
        "type": "string", "format": "date-time", "title": "Requested At",
        "description": "Optional. When the cashier scanned the product. The reference implementation "
                       "accepts and ignores it.",
        "example": "2026-10-14T17:03:00Z"})
    vreq["example"] = {"serial": "X123", "sku": "NMB-P8-128", "store_id": "store_a",
                       "requested_at": "2026-10-14T17:03:00Z"}

    vres = schemas["VerifyResponse"]
    vres["description"] = ("The brand's verdict. Only VERIFIED lets the platform create a PayPal order; the "
                           "verification_id is stored in the order's custom_id.")
    vres["properties"]["verification_id"].update(
        description="Unique id of this check. Quote it when confirming the sale.", example="ver_3f9a1c2b7d4e")
    vres["properties"]["result"] = {"type": "string", "title": "Result", "enum": ["VERIFIED", "NOT_VERIFIED"],
                                    "description": "Whether the brand stands behind this unit at this store."}
    vres["properties"]["reason_code"] = {
        "anyOf": [{"type": "string", "enum": REASON_CODES}, {"type": "null"}], "title": "Reason Code",
        "description": (
            "Null when VERIFIED. Otherwise why not:\n"
            "- UNKNOWN_SERIAL: the brand never issued this serial.\n"
            "- SKU_MISMATCH: the serial belongs to a different product.\n"
            "- NOT_IN_CHANNEL: this store is not in the serial's supply chain. Checked before ALREADY_SOLD, "
            "so a clone at the wrong store fails even before the genuine unit sells.\n"
            "- ALREADY_SOLD: the serial was already sold.\n"
            "Codes never reveal which store a serial belongs to.")}

    creq = schemas["ConfirmRequest"]
    creq["description"] = "Sent after the PayPal capture completes, so the brand can mark the serial sold."
    creq["properties"]["paypal_order_id"].update(description="The captured PayPal order.",
                                                 example="5O190127TN364715T")
    creq["properties"].setdefault("captured_at", {
        "type": "string", "format": "date-time", "title": "Captured At",
        "description": "Optional. When PayPal reported the capture. The reference implementation accepts "
                       "and ignores it.", "example": "2026-10-14T17:04:12Z"})
    creq["example"] = {"paypal_order_id": "5O190127TN364715T", "captured_at": "2026-10-14T17:04:12Z"}

    schemas["ConfirmResponse"] = {"type": "object", "title": "ConfirmResponse",
                                  "properties": {"ok": {"type": "boolean", "example": True}},
                                  "required": ["ok"], "example": {"ok": True}}
    schemas["Error"] = ERROR_SCHEMA

    def err(desc: str, example: str) -> dict:
        return {"description": desc, "content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/Error"}, "example": {"detail": example}}}}

    verify = paths["/v1/verify"]["post"]
    _strip_token_header(verify)
    verify.update(
        operationId="verifyProduct", summary="Verify a product before payment", tags=["Verification"],
        description=(
            "Called by the checkout platform when a cashier scans a serialized product, **before** any PayPal "
            "order exists. Return VERIFIED only if the brand stands behind this unit being sold at this store. "
            "How the brand decides is its own business logic. Every call should be logged by the brand.\n\n"
            "Always answer 200 with a verdict for well-formed requests, including unknown serials; use "
            "reason_code to say why a check failed."))
    verify["responses"] = {
        "200": {"description": "Verdict for this unit at this store.", "content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/VerifyResponse"},
            "examples": {
                "verified": {"summary": "Genuine unit at an authorized store",
                             "value": {"verification_id": "ver_3f9a1c2b7d4e", "result": "VERIFIED",
                                       "reason_code": None}},
                "not_in_channel": {"summary": "Same serial at a store outside its supply chain",
                                   "value": {"verification_id": "ver_8b20e5aa91c3", "result": "NOT_VERIFIED",
                                             "reason_code": "NOT_IN_CHANNEL"}},
                "already_sold": {"summary": "Serial already sold",
                                 "value": {"verification_id": "ver_c41d09e7f2b8", "result": "NOT_VERIFIED",
                                           "reason_code": "ALREADY_SOLD"}},
                "unknown_serial": {"summary": "Serial the brand never issued",
                                   "value": {"verification_id": "ver_0e6f3b5c8a17", "result": "NOT_VERIFIED",
                                             "reason_code": "UNKNOWN_SERIAL"}}}}}},
        "401": err("Missing or wrong X-Node-Token.", "bad node token"),
        "422": verify["responses"]["422"],
    }
    verify["requestBody"]["content"]["application/json"]["examples"] = {
        "store_a": {"summary": "Demo serial at its own store", "value": {
            "serial": "X123", "sku": "NMB-P8-128", "store_id": "store_a", "requested_at": "2026-10-14T17:03:00Z"}},
        "store_b": {"summary": "Same serial at another store", "value": {
            "serial": "X123", "sku": "NMB-P8-128", "store_id": "store_b", "requested_at": "2026-10-14T17:09:00Z"}},
    }

    confirm = paths["/v1/verify/{verification_id}/confirm"]["post"]
    _strip_token_header(confirm)
    for p in confirm.get("parameters", []):
        if p["name"] == "verification_id":
            p.update(description="The verification_id returned by verifyProduct (must be VERIFIED).",
                     example="ver_3f9a1c2b7d4e")
    confirm.update(
        operationId="confirmSale", summary="Confirm the sale after PayPal capture", tags=["Verification"],
        description=("Called once the PayPal capture completes. The brand marks the serial sold, so any later "
                     "attempt to sell the same serial fails with ALREADY_SOLD (or NOT_IN_CHANNEL at another "
                     "store). Idempotent: confirming twice is harmless."))
    confirm["requestBody"]["content"]["application/json"]["example"] = creq["example"]
    confirm["responses"] = {
        "200": {"description": "Sale recorded.", "content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/ConfirmResponse"}, "example": {"ok": True}}}},
        "401": err("Missing or wrong X-Node-Token.", "bad node token"),
        "404": err("No VERIFIED check with that id.", "no verified check with that id"),
        "422": confirm["responses"]["422"],
    }

    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "TrustLedger Brand Verification API",
            "version": VERSION,
            "summary": "The contract a brand implements so its products can be verified before payment.",
            "description": (
                "TrustLedger makes product authenticity a condition of payment. At checkout, the platform asks "
                "the brand whether a serialized product may be sold at this store. Only a VERIFIED answer "
                "leads to a PayPal order, and the verification_id travels in the order's custom_id. After "
                "capture, the platform confirms the sale so the brand can mark the serial sold.\n\n"
                "Brands implement these two endpoints. The reference implementation is TrustLedger's mock "
                "brand (Nimbus, fictional). Responses must not reveal which store a serial belongs to."),
            "license": {"name": "MIT", "identifier": "MIT"},
        },
        "servers": [
            {"url": "http://localhost:8001", "description": "Local mock brand (uvicorn / docker compose)"},
            {"url": "https://{brandHost}", "description": "A brand's own deployment",
             "variables": {"brandHost": {"default": "verify.example-brand.com"}}},
        ],
        "security": [{"NodeToken": []}],
        "tags": [{"name": "Verification", "description": "Pre-payment product verification."}],
        "paths": paths,
        "components": {"schemas": schemas, "securitySchemes": NODE_TOKEN_SCHEME},
    }
    _prune_schemas(spec)
    return spec


# --------------------------------------------------------------------------- platform (api service)

PLATFORM_DOCS = {
    ("/checkout/scan", "post"): ("scanProduct", "Scan a product: verify with the brand, then create the PayPal order",
                                 "Calls the brand's POST /v1/verify. VERIFIED: creates a PayPal order (intent "
                                 "CAPTURE, custom_id = verification_id) and returns its id. NOT_VERIFIED: no PayPal "
                                 "call is made; a case opens for the brand and the reason is returned."),
    ("/checkout/{checkout_id}/capture", "post"): ("captureCheckout", "Capture the payment",
                                                  "Captures the PayPal order, confirms the sale with the brand, "
                                                  "and returns the receipt."),
    ("/receipts/{checkout_id}", "get"): ("getReceipt", "Receipt", "Receipt with verification and PayPal order ids."),
    ("/cases", "get"): ("listCases", "List investigation cases", "Newest first, with a findings count."),
    ("/cases/{case_id}", "get"): ("getCase", "Case detail", "A case and every agent step, in order."),
    ("/stores", "get"): ("listStores", "List stores", None),
    ("/health", "get"): ("health", "Health check", None),
    ("/paypal/webhooks", "post"): ("paypalWebhook", "PayPal webhook receiver",
                                   "Verifies the PayPal signature before handling the event."),
}


def platform_spec() -> dict:
    from backend.api.main import app

    spec = copy.deepcopy(app.openapi())
    spec["openapi"] = "3.1.0"
    spec["info"] = {
        "title": "TrustLedger Platform API", "version": VERSION,
        "description": ("The api service: checkout gate, receipts, PayPal webhooks, cases for the brand cockpit, "
                        "and the question console. /internal/* is for the worker and needs X-Node-Token."),
        "license": {"name": "MIT", "identifier": "MIT"},
    }
    spec["servers"] = [{"url": "http://localhost:8000", "description": "Local"},
                       {"url": "https://{apiHost}", "description": "Hosted (Render)",
                        "variables": {"apiHost": {"default": "trustledger-api.onrender.com"}}}]
    spec.setdefault("components", {})["securitySchemes"] = NODE_TOKEN_SCHEME
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            had_token = any(p.get("in") == "header" and p.get("name", "").lower() == "x-node-token"
                            for p in op.get("parameters", []))
            _strip_token_header(op)
            if had_token:
                op["security"] = [{"NodeToken": []}]
            if path.startswith("/internal/"):
                op["tags"] = ["internal"]
            doc = PLATFORM_DOCS.get((path, method))
            if doc:
                op["operationId"], op["summary"] = doc[0], doc[1]
                if doc[2]:
                    op["description"] = doc[2]
    spec.setdefault("components", {}).setdefault("schemas", {})["Error"] = ERROR_SCHEMA
    capture_op = spec.get("paths", {}).get("/checkout/{checkout_id}/capture", {}).get("post")
    if capture_op:
        capture_op.setdefault("responses", {})["409"] = {
            "description": "Checkout is not awaiting payment, or buyer has not approved the PayPal order yet.",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"},
                                             "example": {"detail": "checkout is not awaiting payment"}}},
        }
    return spec


# --------------------------------------------------------------------------- output

def render(spec: dict) -> tuple[str, str]:
    if yaml is not None:
        class _Dumper(yaml.SafeDumper):
            pass
        _Dumper.add_representer(type(None), lambda d, _: d.represent_scalar("tag:yaml.org,2002:null", "null"))
        text = "# Generated by scripts/export_openapi.py from the FastAPI apps. Do not edit by hand.\n"
        text += yaml.dump(spec, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=110)
        return ".yaml", text
    return ".json", json.dumps(spec, indent=2) + "\n"


def main() -> int:
    check = "--check" in sys.argv[1:]
    OUT.mkdir(exist_ok=True)
    stale = []
    for stem, build in (("brand-verification", brand_verification_spec), ("platform", platform_spec)):
        ext, text = render(build())
        path = OUT / f"{stem}{ext}"
        if check:
            if not path.exists() or path.read_text() != text:
                stale.append(path.name)
            continue
        path.write_text(text)
        print(f"wrote {path.relative_to(ROOT)} ({len(text.splitlines())} lines)")
    if stale:
        print("stale: " + ", ".join(stale) + " -> run: uv run python scripts/export_openapi.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
