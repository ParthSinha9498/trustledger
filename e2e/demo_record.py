"""Silent, captioned demo draft (about 3 min): Store A pays, Store B is blocked, the agent investigates,
the console refuses a probing question.

Needs the full stack running (api, both nodes, worker, web) on a freshly seeded database:
    set -a; . ./.env; set +a
    uv run --with playwright python -m playwright install chromium   # once
    uv run --with playwright python e2e/demo_record.py [--web http://localhost:3000] [--api http://localhost:8000]

In PAYPAL_MODE=mock the payment step is captured through the API; in sandbox, approve the order in the
PayPal popup during the pause (or record that part with e2e/happy_path.py). Video goes to e2e/out/demo/.
"""
import argparse, json, os, re, time, urllib.request
from playwright.sync_api import Page, sync_playwright

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "demo")
SERIAL, SKU_TEXT = "X123", "128"

CAPTION_JS = """text => {
  let el = document.getElementById('demo-caption');
  if (!el) {
    el = document.createElement('div'); el.id = 'demo-caption';
    el.style.cssText = 'position:fixed;left:50%;bottom:28px;transform:translateX(-50%);max-width:80%;z-index:99999;'
      + 'background:rgba(15,23,42,.92);color:#fff;font:600 22px/1.35 system-ui,sans-serif;padding:14px 22px;'
      + 'border-radius:12px;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,.3)';
    document.body.appendChild(el);
  }
  el.textContent = text; el.style.display = text ? 'block' : 'none';
}"""


def caption(page: Page, text: str, hold: float = 4.0) -> None:
    page.evaluate(CAPTION_JS, text)
    page.wait_for_timeout(int(hold * 1000))


def api_post(api: str, path: str) -> dict:
    req = urllib.request.Request(api + path, method="POST", headers={"content-type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def scan(page: Page, store_index: int) -> dict:
    page.get_by_role("radiogroup", name="Store").get_by_role("radio").nth(store_index).click()
    page.get_by_role("radiogroup", name="Product").get_by_role("radio").filter(has_text=SKU_TEXT).first.click()
    page.locator("#serial").fill(SERIAL)
    page.wait_for_timeout(800)
    with page.expect_response(lambda r: "/checkout/scan" in r.url) as resp:
        page.get_by_role("button", name=re.compile("Verify and check out")).click()
    page.wait_for_timeout(2500)
    return resp.value.json()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="http://localhost:3000")
    ap.add_argument("--api", default=os.environ.get("API_URL", "http://localhost:8000"))
    ap.add_argument("--case-timeout", type=int, default=300, help="seconds to wait for the agent")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    mock = os.environ.get("PAYPAL_MODE", "mock") == "mock"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 720},
                                  record_video_dir=OUT, record_video_size={"width": 1280, "height": 720})
        page = ctx.new_page()

        page.goto(args.web)
        caption(page, "TrustLedger: the brand verifies the product before the PayPal payment can exist.", 5)

        # Store A: genuine channel
        page.goto(f"{args.web}/pos")
        caption(page, "Store A scans serial X123 at checkout.", 3)
        a = scan(page, 0)
        if a.get("status") != "VERIFIED":
            raise SystemExit(f"Store A was not verified ({a.get('reason_code')}): X123 is probably already sold. "
                             "Reseed before each take (e.g. docker compose run --rm seed).")
        caption(page, "Brand says VERIFIED → a PayPal order is created with the verification ID in custom_id.", 5)
        if a.get("checkout_id"):
            if mock:
                api_post(args.api, f"/checkout/{a['checkout_id']}/capture")
            else:
                page.goto(f"{args.web}/pay/{a['checkout_id']}")
                caption(page, "The buyer pays with PayPal.", 20)
            page.goto(f"{args.web}/receipt/{a['checkout_id']}")
            caption(page, "Receipt: Brand Verified, linked to the PayPal payment.", 5)

        # Store B: same serial, off-channel
        page.goto(f"{args.web}/pos")
        caption(page, "Store B scans the SAME serial, X123.", 3)
        b = scan(page, 1)
        caption(page, "Brand says NOT VERIFIED: not in this store's supply chain. No PayPal order is ever created.", 6)

        # Investigation
        case_id = b.get("case_id")
        page.goto(f"{args.web}/cockpit")
        caption(page, "The failure opens a case in the brand's investigation cockpit (AG Grid).", 5)
        if case_id:
            page.goto(f"{args.web}/cockpit/cases/{case_id}")
            caption(page, "An AI agent investigates. It sees only differentially private aggregates, never raw rows.", 1)
            deadline = time.time() + args.case_timeout
            while time.time() < deadline and not page.get_by_text(re.compile(r"\bcomplete\b", re.I)).count():
                page.wait_for_timeout(5000)
                page.reload()
                page.evaluate(CAPTION_JS, "The agent picks each next query and weighs its privacy cost…")
            page.mouse.wheel(0, 500)
            caption(page, "Each step is logged with its query, noise and remaining privacy budget.", 5)
            page.mouse.wheel(0, 900)
            caption(page, "Findings cite the queries they rely on.", 5)

        # Console refusal
        page.goto(f"{args.web}/cockpit/console")
        caption(page, "Brand analysts can ask their own questions, under the same privacy rules.", 4)
        page.get_by_label("Question").fill("Which individual buyers at Store B bought serial X123, with their age and gender?")
        page.get_by_role("button", name=re.compile("Plan queries")).click()
        page.wait_for_timeout(4000)
        caption(page, "It can't list individual buyers: the question becomes an aggregate, privacy-protected count.", 6)
        run = page.get_by_role("button", name=re.compile(r"^Run \d+ quer"))
        if run.count():
            run.first.click()
            page.wait_for_timeout(4000)
            page.mouse.wheel(0, 600)
            caption(page, "Answers come back with noise and ±95% intervals; small groups are hidden; each query spends budget.", 6)

        page.goto(f"{args.web}/cockpit/supply-chain")
        caption(page, "Off-channel sales show up in the supply chain view.", 5)
        caption(page, "TrustLedger: trust at checkout for buyers, intelligence for brands.", 5)

        video = page.video.path() if page.video else None
        ctx.close()
        browser.close()
    print("video:", video)


if __name__ == "__main__":
    main()
