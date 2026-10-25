"""TrustLedger brand onboarding: verify a serial before PayPal payment."""
import os
import sys
import httpx


def verify_product(serial: str, sku: str, store_id: str) -> dict:
    base_url = os.environ.get("TRUSTLEDGER_API_URL") or os.environ.get("BRAND_NODE_URL", "http://localhost:8001")
    api_key = os.environ.get("BRAND_API_KEY") or os.environ.get("NODE_SHARED_TOKEN")
    if not api_key:
        sys.exit("Error: BRAND_API_KEY (or NODE_SHARED_TOKEN) environment variable is required.")

    url = f"{base_url.rstrip('/')}/v1/verify"
    headers = {"X-Node-Token": api_key, "Content-Type": "application/json"}
    payload = {"serial": serial, "sku": sku, "store_id": store_id}

    response = httpx.post(url, json=payload, headers=headers, timeout=10.0)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # Example using Nimbus P8 128GB at Store A
    serial = sys.argv[1] if len(sys.argv) > 1 else "X123"
    sku = sys.argv[2] if len(sys.argv) > 2 else "NMB-P8-128"
    store_id = sys.argv[3] if len(sys.argv) > 3 else "store_a"

    data = verify_product(serial, sku, store_id)
    result = data.get("result")
    reason = data.get("reason_code")
    vid = data.get("verification_id")

    if result == "VERIFIED":
        print(f"VERIFIED: {serial} is genuine for {store_id} (verification_id={vid}). Proceed to PayPal checkout.")
    else:
        print(f"NOT_VERIFIED: {serial} failed verification ({reason}). Do not create PayPal order; case logged.")
