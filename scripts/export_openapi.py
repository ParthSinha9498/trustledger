"""Export TrustLedger's OpenAPI specs from the FastAPI apps.

    uv run python scripts/export_openapi.py           # write openapi/*.yaml
    uv run python scripts/export_openapi.py --check   # exit 1 if the committed specs are stale

Writes
  openapi/brand-verification.yaml   the contract brands implement (POST /v1/verify, POST /v1/verify/{id}/confirm).
                                    This is the file to import into SDK and docs generators, and into Postman.
  openapi/platform.yaml             the api service (checkout gate, receipts, cases, console, ...)

Schemas and paths come from the running code (FastAPI's app.openapi()); this script only adds the
contract wording, examples, enums and the X-Node-Token security scheme. If PyYAML is missing the
specs are written as .json instead.
"""
from __future__ import annotations

import copy
import json
import os
import re
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


# --------------------------------------------------------------------------- APIMatic polish

EXAMPLE_HINTS = {
    "serial": "X123", "sku": "NMB-P8-128", "store_id": "store_a", "paypal_order_id": "5O190127TN364715T",
    "checkout_id": "chk_3f9a1c2b7d4e", "case_id": "case_7c1d2e3f4a5b", "verification_id": "ver_3f9a1c2b7d4e",
    "order_id": "5O190127TN364715T", "email": "buyer@example.com",
}


def _humanize(name: str) -> str:
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).replace("_", " ").strip()
    return (words[:1].upper() + words[1:]).rstrip(".") + "."


def _example_value(name: str, schema: dict):
    """A plausible scalar example for a field, or None when there is no safe scalar to show."""
    if not isinstance(schema, dict) or "$ref" in schema:
        return None
    if schema.get("enum"):
        return schema["enum"][0]
    if "anyOf" in schema:  # Optional[X] renders as anyOf [X, null]: show the X
        for sub in schema["anyOf"]:
            ex = _example_value(name, sub)
            if ex is not None:
                return ex
        return None
    kind = schema.get("type")
    if kind == "string":
        if schema.get("format") == "date-time":
            return "2026-10-14T17:03:00Z"
        return EXAMPLE_HINTS.get(name, name.replace("_", "-"))
    if kind == "integer":
        return 1
    if kind == "number":
        return 1.0
    if kind == "boolean":
        return True
    if kind == "array":
        items = schema.get("items", {})
        if isinstance(items, dict) and "$ref" not in items and items.get("type") == "string":
            return [_example_value(name, items)]
        return []
    if kind == "object":
        return {}
    return None


def _fix_schema(s: dict, name: str | None, is_component: bool) -> None:
    if not isinstance(s, dict) or "$ref" in s:
        return
    if s.get("type") == "object" and not s.get("properties") and "additionalProperties" not in s:
        # Free-form object (e.g. FastAPI's ValidationError.ctx): declare it so tooling does not reject it.
        s["additionalProperties"] = True
        s.setdefault("description", "Extra context for the error; keys vary by error type.")
    if not is_component:
        s.pop("title", None)  # FastAPI repeats field titles; duplicate titles fail APIMatic validation
    if not s.get("description") and name:
        s["description"] = _humanize(name) if not is_component else _humanize(name)
    if "example" not in s and "default" not in s and name and not is_component:
        ex = _example_value(name, s)
        if ex is not None:
            s["example"] = ex
    for pname, ps in (s.get("properties") or {}).items():
        _fix_schema(ps, pname, False)
    items = s.get("items")
    if isinstance(items, dict):
        _fix_schema(items, name, False)
    for key in ("anyOf", "oneOf", "allOf"):
        for sub in s.get(key) or []:
            _fix_schema(sub, name, False)


def _object_example(schema: dict, schemas: dict, depth: int = 0):
    """Build a response/request example from a schema's properties (None when nothing usable)."""
    if depth > 4:
        return None
    if "$ref" in schema:
        target = schemas.get(schema["$ref"].rsplit("/", 1)[1], {})
        if "example" in target:
            return copy.deepcopy(target["example"])
        return _object_example(target, schemas, depth + 1)
    if "example" in schema:
        return copy.deepcopy(schema["example"])
    props = schema.get("properties")
    if not props:
        return None
    out = {}
    for pname, ps in props.items():
        if "$ref" in ps:
            sub = _object_example(ps, schemas, depth + 1)
        else:
            sub = ps.get("example", _example_value(pname, ps))
        if sub is not None:
            out[pname] = sub
    return out or None


def polish(spec: dict) -> dict:
    """Fill the metadata APIMatic's validator asks for: descriptions, examples, tags, contact, sorted codes.

    Only wording and examples are added here. Paths, schemas and field names come from the code.
    """
    schemas = spec.setdefault("components", {}).setdefault("schemas", {})
    for name, sch in schemas.items():
        _fix_schema(sch, name, True)
        if not sch.get("description"):
            sch["description"] = _humanize(re.sub(r"(?<!^)(?=[A-Z])", " ", name))
    for name, sch in schemas.items():
        for pname, ps in (sch.get("properties") or {}).items():
            _fix_schema(ps, pname, False)
    spec.setdefault("info", {}).setdefault("contact", {
        "name": "TrustLedger (fictional demo project)",
        "url": "https://github.com/parthsinha9498/trustledger"})

    used_tags: dict[str, str] = {}
    for path, ops in spec.get("paths", {}).items():
        for method, op in ops.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            if not op.get("tags"):
                first = path.strip("/").split("/")[0] or "root"
                op["tags"] = [first]
            for t in op["tags"]:
                used_tags.setdefault(t, f"Operations for {t}.")
            if not op.get("description"):
                op["description"] = op.get("summary") or _humanize(op.get("operationId", "operation"))
            for p in op.get("parameters", []):
                p.setdefault("description", _humanize(p["name"]))
                p.get("schema", {}).pop("title", None)  # repeated FastAPI titles fail validation
                if "example" not in p and "examples" not in p:
                    ex = _example_value(p["name"], p.get("schema", {}))
                    if ex is not None:
                        p["example"] = ex
            body = op.get("requestBody")
            if body:
                body.setdefault("description", f"Request body for {op.get('summary', op.get('operationId', 'this call'))}.")
                for media in body.get("content", {}).values():
                    if "example" not in media and "examples" not in media:
                        ex = _object_example(media.get("schema", {}), schemas)
                        if ex is not None:
                            media["example"] = ex
            for code in list(op.get("responses", {})):
                resp = op["responses"][code]
                resp.setdefault("description", "Response.")
                for media in resp.get("content", {}).values():
                    if "example" not in media and "examples" not in media:
                        ex = _object_example(media.get("schema", {}), schemas)
                        if ex is not None:
                            media["example"] = ex
            op["responses"] = {k: op["responses"][k] for k in sorted(op.get("responses", {}), key=str)}
    spec["tags"] = [{"name": t, "description": d} for t, d in sorted(used_tags.items())]
    for server in spec.get("servers", []):
        server.setdefault("description", "Environment.")
        for var in server.get("variables", {}).values():
            var.setdefault("description", "Host name of the deployment.")
    return spec


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
    return polish(spec)


# --------------------------------------------------------------------------- platform (api service)

PLATFORM_DOCS = {
    ("/checkout/scan", "post"): ("scanProduct", "Scan a product and create its PayPal order",
                                 "Calls the brand's POST /v1/verify. VERIFIED: creates a PayPal order (intent "
                                 "CAPTURE, custom_id = verification_id) and returns its id. NOT_VERIFIED: no PayPal "
                                 "call is made; a case opens for the brand and the reason is returned."),
    ("/checkout/{checkout_id}/capture", "post"): ("captureCheckout", "Capture the payment",
                                                  "Captures the PayPal order, confirms the sale with the brand, "
                                                  "and returns the receipt."),
    ("/checkout/{checkout_id}/pay-test-card", "post"): (
        "payCheckoutWithTestCard", "Pay with a PayPal sandbox test card (sandbox only)",
        "Sandbox demo path, refused in live mode. The server confirms the existing PayPal order (created only "
        "after VERIFIED) with a PayPal sandbox test card from its environment (Orders v2 "
        "confirm-payment-source), then runs the normal capture and returns the receipt. No buyer login."),
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
    platform_error_schema = {
        "type": "object",
        "properties": {
            "detail": {
                "description": "Error details, either as a human-readable string or a PayPal error object.",
                "oneOf": [
                    {"type": "string", "example": "checkout is not awaiting payment"},
                    {
                        "type": "object",
                        "properties": {
                            "paypal_issue": {"type": "string", "example": "ORDER_NOT_APPROVED"},
                            "message": {"type": "string", "example": "Order has not been approved by buyer"},
                            "paypal_status": {"type": "string", "example": "FAILED"},
                        },
                    },
                ],
            }
        },
        "required": ["detail"],
    }
    spec.setdefault("components", {}).setdefault("schemas", {})["Error"] = platform_error_schema
    capture_op = spec.get("paths", {}).get("/checkout/{checkout_id}/capture", {}).get("post")
    if capture_op:
        capture_op.setdefault("responses", {})["409"] = {
            "description": "Checkout is not awaiting payment, or buyer has not approved the PayPal order yet.",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"},
                    "example": {
                        "detail": {
                            "paypal_issue": "ORDER_NOT_APPROVED",
                            "message": "Order has not been approved by buyer",
                        }
                    },
                }
            },
        }
        capture_op["responses"]["502"] = {
            "description": "PayPal upstream error or capture failed.",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"},
                    "example": {"detail": {"paypal_status": "FAILED"}},
                }
            },
        }
    card_op = spec.get("paths", {}).get("/checkout/{checkout_id}/pay-test-card", {}).get("post")
    if card_op:
        def err(desc: str, example) -> dict:
            return {"description": desc, "content": {"application/json": {
                "schema": {"$ref": "#/components/schemas/Error"}, "example": {"detail": example}}}}
        card_op["responses"].update({
            "403": err("Live mode: test-card payments are sandbox only.", "test-card payments are sandbox only"),
            "404": err("Unknown checkout.", "unknown checkout"),
            "409": err("Blocked (no PayPal order exists) or already paid.",
                       "checkout is not awaiting payment (blocked checkouts have no PayPal order)"),
            "502": err("PayPal upstream error or capture failed.", {"paypal_status": "FAILED"}),
            "503": err("No sandbox test card configured on the server.",
                       "SANDBOX_TEST_CARD_NUMBER and SANDBOX_TEST_CARD_EXPIRY are not set"),
        })
    return polish(spec)


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
