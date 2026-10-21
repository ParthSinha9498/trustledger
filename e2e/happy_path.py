"""Happy path against a running stack in PAYPAL_MODE=sandbox:
genuine scan -> sandbox order -> sandbox buyer approves (headless Chromium) -> capture -> receipt.

    set -a; . ./.env; set +a
    uv run --with playwright python -m playwright install chromium   # once
    uv run --with playwright python e2e/happy_path.py

Needs SANDBOX_BUYER_EMAIL/PASSWORD in .env and a US-region sandbox seller app. Screenshots go to e2e/out/.
"""
import json, os, sys, urllib.request
import psycopg
from playwright.sync_api import sync_playwright

API = "http://localhost:8000"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:800]}


c = psycopg.connect("postgresql://postgres:postgres@localhost:5433/trustledger_brand")
serial, sku, store = c.execute(
    "select s.serial,s.sku,cs.store_id from serials s join channel_shipments cs using(batch_id) "
    "where s.sold_store_id is null offset 5 limit 1").fetchone()
scan = call("POST", "/checkout/scan", {"store_id": store, "serial": serial, "sku": sku, "amount": 49.99})
print("SCAN", scan)
order = scan["paypal_order_id"]

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto(f"https://www.sandbox.paypal.com/checkoutnow?token={order}", timeout=60000)
    pg.fill("#email", os.environ["SANDBOX_BUYER_EMAIL"])
    if pg.is_visible("#btnNext"):
        pg.click("#btnNext")
    pg.fill("#password", os.environ["SANDBOX_BUYER_PASSWORD"], timeout=30000)
    pg.click("#btnLogin")
    pg.wait_for_timeout(12000)
    pg.screenshot(path=f"{OUT}/review.png")
    for sel in ["#payment-submit-btn", "button[data-testid='submit-button-initial']", "text=Continue to Review Order",
                "text=Complete Purchase", "text=Continue", "text=Pay Now"]:
        if pg.locator(sel).first.is_visible():
            pg.locator(sel).first.click()
            print("clicked", sel)
            break
    pg.wait_for_timeout(8000)
    pg.screenshot(path=f"{OUT}/after.png")
    print("URL", pg.url[:120])
    b.close()

print("CAPTURE", call("POST", f"/checkout/{scan['checkout_id']}/capture"))
print("RECEIPT", call("GET", f"/receipts/{scan['checkout_id']}"))
