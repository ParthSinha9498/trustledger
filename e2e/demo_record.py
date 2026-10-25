"""Pitch demo recorder (~2:45, silent, captioned), storyboard v3 (docs/demo/VOICEOVER.md).

Needs the full stack running (api, both nodes, worker, web) on a freshly seeded database:
    set -a; . ./.env; set +a
    uv run --with playwright python -m playwright install chromium   # once
    uv run --with playwright python e2e/demo_record.py [--web http://localhost:3000] [--api http://localhost:8000]
    uv run --with imageio-ffmpeg python e2e/demo_cut.py              # remove the waits → e2e/out/demo/demo.mp4

Story cards come from the web app's /story?card=<id> route; if it isn't there yet, a plain built-in card is used.
In PAYPAL_MODE=mock the payment is captured through the API; in sandbox, approve the order in the PayPal popup
during the pause. Video and cut markers go to e2e/out/demo/.
"""
import argparse, base64, json, os, re, time, urllib.request
from playwright.sync_api import Locator, Page, sync_playwright

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "demo")
SERIAL, SKU_TEXT = "X123", "128"

# Injected into every page: a visible cursor that follows the mouse, with a ripple on click.
CURSOR_JS = """(() => {
  if (window.__demoCursor) return; window.__demoCursor = true;
  const add = () => {
    const c = document.createElement('div'); c.id = 'demo-cursor';
    c.style.cssText = 'position:fixed;left:-40px;top:-40px;width:22px;height:22px;border-radius:50%;z-index:100000;'
      + 'background:rgba(37,99,235,.35);border:2px solid #2563eb;pointer-events:none;transform:translate(-50%,-50%);'
      + 'transition:left .04s linear, top .04s linear';
    document.body.appendChild(c);
    addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', e => {
      const r = document.createElement('div');
      r.style.cssText = `position:fixed;left:${e.clientX}px;top:${e.clientY}px;width:16px;height:16px;border-radius:50%;`
        + 'border:3px solid #2563eb;transform:translate(-50%,-50%);pointer-events:none;z-index:100000;'
        + 'transition:all .5s ease-out;opacity:1';
      document.body.appendChild(r);
      requestAnimationFrame(() => { r.style.width = r.style.height = '60px'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 600);
    }, true);
  };
  document.readyState === 'loading' ? addEventListener('DOMContentLoaded', add) : add();
})()"""

CAPTION_JS = """text => {
  let el = document.getElementById('demo-caption');
  if (!el) {
    el = document.createElement('div'); el.id = 'demo-caption';
    el.style.cssText = 'position:fixed;left:50%;bottom:24px;transform:translateX(-50%);max-width:82%;z-index:99999;'
      + 'background:rgba(15,23,42,.92);color:#fff;font:600 22px/1.35 system-ui,sans-serif;padding:12px 22px;'
      + 'border-radius:12px;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,.3)';
    document.body.appendChild(el);
  }
  el.textContent = text; el.style.display = text ? 'block' : 'none';
}"""

RING_JS = """([x, y, w, h]) => {
  const r = document.createElement('div'); r.className = 'demo-ring';
  r.style.cssText = `position:fixed;left:${x - 8}px;top:${y - 8}px;width:${w + 16}px;height:${h + 16}px;z-index:99998;`
    + 'border:3px solid #f59e0b;border-radius:12px;pointer-events:none;box-shadow:0 0 0 6px rgba(245,158,11,.25);'
    + 'animation:demoPulse 1s ease-in-out infinite alternate';
  if (!document.getElementById('demo-ring-style')) {
    const s = document.createElement('style'); s.id = 'demo-ring-style';
    s.textContent = '@keyframes demoPulse{from{box-shadow:0 0 0 4px rgba(245,158,11,.15)}to{box-shadow:0 0 0 12px rgba(245,158,11,.35)}}';
    document.head.appendChild(s);
  }
  document.body.appendChild(r);
}"""

# Plain fallback cards until the web app's /story route exists.
FALLBACK = {
    "hook": ["One phone. One serial number. Two stores.", "Only one of them is selling the real thing."],
    "problem": ["USD 467 billion in counterfeit goods traded in a year",
                "up to 2.3% of world trade · smartphones: 12.9% of sales (EUR 45.3B, 2015)",
                "OECD / EUIPO 2025 (2021 data) · EUIPO / ITU"],
    "gap": ["Verification exists. Nobody uses it.", "Optional · separate from paying · different for every brand"],
    "idea": ["Make authenticity a condition of payment.", "Scan → brand verifies → PayPal payment. Not verified → no payment."],
    "how": ["Data never moves.", "Questions travel to the brand and PayPal nodes; only private aggregates come back."],
    "s1": ["Scenario 1", "A genuine phone at an authorized store"],
    "s2": ["Scenario 2", "The same serial at Store C outside the supply chain"],
    "s3": ["Scenario 3", "The brand investigates"],
    "business": ["How does this pay for itself?",
                 "USD 150B+ a year on market insights (ESOMAR, 2024 data). Survey results take weeks.",
                 "In a 2024 Pew survey, 18% of responses were flagged as bogus."],
    "s4": ["Scenario 4", "Brand insights from verified purchases"],
    "analyst": ["AI Analyst", "Natural language queries answered without exposing raw buyer records"],
    "guarantee": ["Buyers stay anonymous: one fixed privacy limit per brand, for life",
                  "Differential privacy (OpenDP) · internal red-team: 11 attack types, none pinned down a single buyer"],
    "levels": ["One API. Every checkout.",
               "Brand: verification API + node · PayPal: checkout gate + private node · Seller: one SDK call (APIMatic)"],
    "close": ["Brands pay for insights; the checkout check is free for shoppers.",
              "Trust for buyers. Intelligence for brands. A stronger PayPal network."],
}


class Recorder:
    def __init__(self, page: Page, web: str):
        self.page, self.web, self.t0, self.marks = page, web, time.monotonic(), []

    def mark(self, kind: str, label: str = "") -> None:
        self.marks.append({"t": round(time.monotonic() - self.t0, 2), "kind": kind, "label": label})

    def wait(self, s: float) -> None:
        self.page.wait_for_timeout(int(s * 1000))

    def caption(self, text: str, hold: float = 4.0) -> None:
        self.page.evaluate(CAPTION_JS, text)
        self.wait(hold)

    def card(self, cid: str, hold: float = 5.0) -> None:
        self.mark("scene", cid)
        t0 = time.monotonic()
        r = self.page.goto(f"{self.web}/story?card={cid}")
        if r is not None and r.ok and self._wait_ready():  # animation finished; it counts toward the hold
            self.wait(max(0.5, hold - (time.monotonic() - t0)))
            return
        lines = FALLBACK[cid]
        html = "".join(f"<p style='margin:.4em 0;font-size:{44 if i == 0 else 26}px;opacity:{1 if i < 2 else .6}'>{l}</p>"
                       for i, l in enumerate(lines))
        self.page.set_content("<body style='margin:0;height:100vh;display:grid;place-items:center;background:#0b1220;"
                              f"color:#f8fafc;font-family:system-ui;text-align:center;padding:0 80px'><div>{html}</div></body>")
        self.wait(hold)

    def _wait_ready(self) -> bool:
        try:
            self.page.wait_for_selector("body[data-ready='1']", timeout=4000)
            return True
        except Exception:
            return False

    def go(self, path: str) -> None:
        self.page.goto(self.web + path)
        self.wait(1.2)

    def click(self, loc: Locator) -> None:
        loc.scroll_into_view_if_needed()
        box = loc.bounding_box()
        if box:
            self.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=25)
            self.wait(0.25)
        loc.click()

    def ring(self, loc: Locator) -> None:
        try:
            loc.scroll_into_view_if_needed(timeout=3000)
            box = loc.bounding_box()
        except Exception:
            return
        if box:
            self.page.evaluate(RING_JS, [box["x"], box["y"], box["width"], box["height"]])

    def unring(self) -> None:
        self.page.evaluate("document.querySelectorAll('.demo-ring').forEach(r => r.remove())")


def api_post(api: str, path: str) -> dict:
    req = urllib.request.Request(api + path, method="POST", headers={"content-type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def scan(rec: Recorder, store: int | str = 0) -> dict:
    page = rec.page
    if isinstance(store, str):
        rec.click(page.get_by_role("radiogroup", name="Store").get_by_text(store, exact=False).first)
    else:
        rec.click(page.get_by_role("radiogroup", name="Store").get_by_role("radio").nth(store))
    rec.click(page.get_by_role("radiogroup", name="Product").get_by_role("radio").filter(has_text=SKU_TEXT).first)
    page.locator("#serial").fill(SERIAL)
    rec.wait(0.6)
    with page.expect_response(lambda r: "/checkout/scan" in r.url) as resp:
        rec.click(page.get_by_role("button", name=re.compile("Verify and check out")))
    rec.wait(2.0)
    return resp.value.json()


def verdict_png(page: Page) -> bytes:
    """Screenshot of the real verification result panel (used for the side-by-side comparison)."""
    return page.locator("section[aria-label='Verification result']").screenshot()


def compare_frame(rec: Recorder, a_png: bytes, b_png: bytes, hold: float) -> None:
    rec.mark("scene", "compare")
    def tile(png: bytes, label: str, color: str) -> str:
        return (f"<figure style='margin:0;flex:1;display:flex;flex-direction:column;gap:14px;align-items:center'>"
                f"<img src='data:image/png;base64,{base64.b64encode(png).decode()}' "
                f"style='max-width:100%;max-height:520px;border-radius:14px;box-shadow:0 10px 40px rgba(0,0,0,.45)'>"
                f"<figcaption style='font:700 24px system-ui;color:{color}'>{label}</figcaption></figure>")
    rec.page.set_content(
        "<body style='margin:0;height:100vh;background:#0b1220;display:flex;gap:36px;align-items:center;"
        "justify-content:center;padding:0 48px;box-sizing:border-box'>"
        + tile(a_png, "Store A · X123 · PayPal order created", "#4ad19a")
        + tile(b_png, "Store C · same X123 · no PayPal order", "#ff8a80") + "</body>")
    rec.wait(hold)


def pay_in_sandbox(rec: Recorder, checkout_id: str) -> None:
    """Buyer approves in PayPal's own window or uses one-click test card; moves to receipt."""
    page = rec.page
    rec.go(f"/pay/{checkout_id}")
    page.wait_for_selector("button:has-text('Pay with test card'), paypal-button", state="visible", timeout=30000)
    test_card = page.locator("button:has-text('Pay with test card')")
    if test_card.count() and test_card.first.is_visible():
        rec.caption("One-click sandbox payment: verified order confirmed", 2.0)
        rec.ring(test_card.first)
        rec.wait(2.0)
        rec.unring()
        rec.click(test_card.first)
        page.wait_for_url(re.compile(r"/receipt/"), timeout=30000)
        return
    rec.caption("The buyer approves in PayPal (sandbox)", 2.5)  # also lets the PayPal SDK finish initialising
    with page.context.expect_page(timeout=30000) as pop_info:
        rec.click(page.locator("paypal-button").first)
    pop = pop_info.value
    pop.set_viewport_size({"width": 1280, "height": 720})  # PayPal opens a narrow window; film it full size
    rec.mark("popup_open", "paypal")
    pop.wait_for_load_state("domcontentloaded", timeout=60000)
    pop.locator("#email").wait_for(state="visible", timeout=60000)
    rec.mark("popup_cut_start", "sandbox login (keeps account details off screen)")
    pop.locator("#email").fill(os.environ["SANDBOX_BUYER_EMAIL"])
    pop.wait_for_timeout(600)
    pop.click("#btnNext")
    pop.locator("#password").wait_for(state="visible", timeout=30000)
    pop.locator("#password").fill(os.environ["SANDBOX_BUYER_PASSWORD"])
    pop.wait_for_timeout(600)
    pop.click("#btnLogin")
    try:
        pop.locator("button:has-text('Complete Purchase'), #payment-submit-btn").first.wait_for(timeout=30000)
    except Exception:
        pass
    rec.mark("popup_cut_end", "review page")
    pop.wait_for_timeout(2500)  # let the viewer read the review page: $899.00, Complete Purchase
    clicked = False
    for _ in range(3):
        for sel in ["#payment-submit-btn", "button[data-testid='submit-button-initial']",
                    "button:has-text('Complete Purchase')", "button:has-text('Pay Now')",
                    "button:has-text('Continue to Review Order')", "button:has-text('Continue')"]:
            try:
                pop.locator(sel).first.click(timeout=8000)
                clicked = True
                break
            except Exception:
                continue
        if clicked or pop.is_closed():
            break
    rec.mark("popup_keep_until", "3 s after Complete Purchase")
    popup_video = pop.video.path() if pop.video else None
    try:
        pop.wait_for_event("close", timeout=30000)
    except Exception:
        pass
    rec.mark("popup_close", str(popup_video or ""))
    page.wait_for_url(re.compile(r"/receipt/"), timeout=60000)


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
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=OUT,
            record_video_size={"width": 1280, "height": 720},
            locale="en-US",
            timezone_id="America/New_York",
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
            permissions=["geolocation"],
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        ctx.add_init_script(CURSOR_JS)
        page = ctx.new_page()
        rec = Recorder(page, args.web)

        # ---- Context (storyboard v3: notes/FLOW.md, docs/demo/VOICEOVER.md)
        rec.card("idea", 8)
        rec.card("problem", 7.5)
        rec.card("gap", 5.5)
        rec.card("how", 10.5)

        # ---- S1: genuine product, authorized store, real PayPal approval
        rec.card("s1", 2.5)
        rec.go("/pos")
        rec.caption("Store A: brand verifies → PayPal order created", 0.5)
        a = scan(rec, 0)
        if a.get("status") != "VERIFIED":
            raise SystemExit(f"Store A was not verified ({a.get('reason_code')}): X123 is probably already sold. "
                             "Reseed before each take (e.g. docker compose run --rm seed).")
        a_png = verdict_png(page)
        rec.ring(page.get_by_text("PayPal order created", exact=False).first)
        rec.wait(3.5)
        rec.unring()
        if mock:
            api_post(args.api, f"/checkout/{a['checkout_id']}/capture")
            rec.go(f"/receipt/{a['checkout_id']}")
        else:
            pay_in_sandbox(rec, a["checkout_id"])
        rec.caption("Receipt: Brand Verified", 3)

        # ---- S2: same serial, store outside the supply chain
        rec.card("s2", 2.5)
        rec.go("/pos")
        rec.caption("Store C, same serial: no PayPal order exists", 0.5)
        b = scan(rec, "Store C")
        b_png = verdict_png(page)
        rec.ring(page.get_by_text("Never created", exact=False).first)
        rec.wait(4.5)
        rec.unring()
        compare_frame(rec, a_png, b_png, 4)

        # ---- S3: the brand investigates; film the data boundary (questions travel, aggregates return)
        rec.card("s3", 2.5)
        case_id = b.get("case_id")
        if case_id:
            rec.go(f"/cockpit/cases/{case_id}")
            rec.caption("AI agent investigates: aggregates only", 2)
            rec.mark("cut_start", "agent running")
            deadline = time.time() + args.case_timeout
            while time.time() < deadline and not page.get_by_text(re.compile(r"\bcomplete\b", re.I)).count():
                rec.wait(5)
                page.reload()
                page.evaluate(CAPTION_JS, "AI agent investigates: aggregates only")
            rec.mark("cut_end", "agent done")
            rec.ring(page.locator("ol.findings li").first)
            rec.wait(4)
            rec.unring()
            boundary = page.get_by_text("What the agent could see").first
            boundary.scroll_into_view_if_needed()
            replay = page.get_by_role("button", name="Replay")
            if replay.count():
                rec.click(replay.first)  # restart the animation now that it is on screen
            rec.caption("Questions travel to the data. Only aggregates come back.", 7)
            earlier = page.locator("summary:has-text('Earlier run')")
            if earlier.count():
                rec.click(earlier.first)
                rec.wait(2.0)

        # ---- S8: supply-chain timeline with Bryntum strip
        rec.mark("scene", "supply-chain")
        rec.go("/cockpit/supply-chain")
        rec.caption("Supply-chain timeline: Distributor 1 shipments sold at Store C", 1.5)
        try:
            page.wait_for_selector("text=What you're looking at", state="visible", timeout=15000)
            rec.ring(page.get_by_text("What you're looking at", exact=False).first)
            rec.wait(4.5)
            rec.unring()
        except Exception:
            pass
        rec.wait(2.5)

        # ---- Business case: the pivot into Brand Insights
        rec.card("business", 11)

        # ---- S4: Brand Insights from verified purchases
        rec.card("s4", 2.5)
        rec.go("/cockpit/console")
        rec.caption("Brand Insights: answers from verified purchases", 1)
        rec.click(page.get_by_role("button", name=re.compile("Which age bands buy", re.I)))
        rec.wait(2)
        try:
            comp_btn = page.get_by_role("button", name=re.compile("Show comparison", re.I))
            if comp_btn.count():
                rec.click(comp_btn.first)
                rec.wait(1.5)
                rec.ring(page.get_by_text("Why brands pay for this", exact=False).first)
                rec.wait(3)
                rec.unring()
        except Exception:
            pass

        try:
            rec.ring(page.get_by_text("Answered in", exact=False).first)
            rec.wait(3)
            rec.unring()
        except Exception:
            pass

        page.mouse.wheel(0, 500)
        rec.wait(1)
        try:
            rec.ring(page.get_by_text("PayPal-side · differentially private", exact=False).first)
            rec.wait(3)
            rec.unring()
        except Exception:
            pass
        rec.wait(2)

        # ---- Scene 11: AI analyst, Scene 12: Guarantee, Scene 13: Onboarding, Scene 14: Close
        rec.card("analyst", 6)
        rec.card("guarantee", 6.5)
        rec.card("levels", 16)
        rec.card("close", 8)

        video = page.video.path() if page.video else None
        ctx.close()
        browser.close()
    with open(os.path.join(OUT, "marks.json"), "w") as f:
        json.dump({"video": str(video), "marks": rec.marks}, f, indent=1)
    print("video:", video)


if __name__ == "__main__":
    main()
