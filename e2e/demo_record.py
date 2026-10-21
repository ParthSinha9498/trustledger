"""Pitch demo recorder (about 3 min, silent, captioned): problem → idea → four scenarios → onboarding → close.

Needs the full stack running (api, both nodes, worker, web) on a freshly seeded database:
    set -a; . ./.env; set +a
    uv run --with playwright python -m playwright install chromium   # once
    uv run --with playwright python e2e/demo_record.py [--web http://localhost:3000] [--api http://localhost:8000]
    uv run --with imageio-ffmpeg python e2e/demo_cut.py              # remove the waits → e2e/out/demo/demo.mp4

Story cards come from the web app's /story?card=<id> route; if it isn't there yet, a plain built-in card is used.
In PAYPAL_MODE=mock the payment is captured through the API; in sandbox, approve the order in the PayPal popup
during the pause. Video and cut markers go to e2e/out/demo/.
"""
import argparse, json, os, re, time, urllib.request
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
                "up to 2.3% of world trade · up to 4.7% of EU imports",
                "OECD / EUIPO, Mapping Global Trade in Fakes 2025 (2021 data)"],
    "phones": ["12.9% of legitimate smartphone sales lost to counterfeits", "≈ EUR 45.3 billion",
               "EUIPO / ITU, smartphone sector study (2015 data)"],
    "gap": ["Verification exists. Nobody uses it.", "Optional · separate from paying · different for every brand"],
    "idea": ["Make authenticity a condition of payment.", "Scan → brand verifies → PayPal payment. Not verified → no payment."],
    "s1": ["Scenario 1", "A genuine phone at an authorized store"],
    "s2": ["Scenario 2", "The same serial at a store outside the supply chain"],
    "s3": ["Scenario 3", "The brand investigates"],
    "s4": ["Scenario 4", "Privacy by design"],
    "onboard": ["One API. Every checkout.", "OpenAPI → SDKs · docs portal · MCP server → POS, e-commerce, AI shopping agents"],
    "close": ["Trust at checkout for buyers.", "Intelligence for brands.", "A more trusted network for PayPal."],
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
        r = self.page.goto(f"{self.web}/story?card={cid}")
        if r is not None and r.ok and self._wait_ready():  # animation finished
            self.wait(hold)
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


def scan(rec: Recorder, store_index: int) -> dict:
    page = rec.page
    rec.click(page.get_by_role("radiogroup", name="Store").get_by_role("radio").nth(store_index))
    rec.click(page.get_by_role("radiogroup", name="Product").get_by_role("radio").filter(has_text=SKU_TEXT).first)
    page.locator("#serial").fill(SERIAL)
    rec.wait(0.6)
    with page.expect_response(lambda r: "/checkout/scan" in r.url) as resp:
        rec.click(page.get_by_role("button", name=re.compile("Verify and check out")))
    rec.wait(2.0)
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
        ctx.add_init_script(CURSOR_JS)
        page = ctx.new_page()
        rec = Recorder(page, args.web)

        # ---- Problem and idea
        rec.card("hook", 5)
        rec.card("problem", 7)
        rec.card("phones", 6)
        rec.card("gap", 7)
        rec.card("idea", 6)

        # ---- Scenario 1: genuine product, authorized store
        rec.card("s1", 3.5)
        rec.go("/pos")
        rec.caption("Store A, an authorized Nimbus retailer, scans serial X123.", 2.5)
        a = scan(rec, 0)
        if a.get("status") != "VERIFIED":
            raise SystemExit(f"Store A was not verified ({a.get('reason_code')}): X123 is probably already sold. "
                             "Reseed before each take (e.g. docker compose run --rm seed).")
        rec.ring(page.get_by_text("PayPal order created", exact=False).first)
        rec.caption("The brand confirms it. Only then does PayPal create the order, with the verification ID in custom_id.", 6)
        rec.unring()
        if mock:
            api_post(args.api, f"/checkout/{a['checkout_id']}/capture")
        else:
            rec.go(f"/pay/{a['checkout_id']}")
            rec.caption("The buyer pays with PayPal.", 20)
        rec.go(f"/receipt/{a['checkout_id']}")
        rec.caption("Receipt: Brand Verified, and the PayPal payment points to the verification.", 5)

        # ---- Scenario 2: same serial, store outside the supply chain
        rec.card("s2", 3.5)
        rec.go("/pos")
        rec.caption("Store B scans the SAME serial, X123.", 2.5)
        b = scan(rec, 1)
        rec.ring(page.get_by_text("Never created", exact=False).first)
        rec.caption("Not verified: this unit was never shipped to Store B. The PayPal order is never created.", 6)
        rec.unring()

        # ---- Scenario 3: the brand investigates
        rec.card("s3", 3.5)
        case_id = b.get("case_id")
        rec.go("/cockpit")
        rec.caption("The failure opens a case in the brand's cockpit, next to ten months of history.", 5)
        if case_id:
            rec.go(f"/cockpit/cases/{case_id}")
            rec.caption("An AI agent investigates, choosing each query itself. It never sees a raw record.", 4)
            rec.mark("cut_start", "agent running")
            deadline = time.time() + args.case_timeout
            while time.time() < deadline and not page.get_by_text(re.compile(r"\bcomplete\b", re.I)).count():
                rec.wait(5)
                page.reload()
            rec.mark("cut_end", "agent done")
            rec.wait(1)
            findings = page.locator("ol.findings li")
            rec.ring(findings.first)
            rec.caption("The finding names where the evidence diverges, and cites the steps it relies on.", 6)
            rec.unring()
            page.mouse.wheel(0, 900)
            rec.wait(1)
            rec.caption("Every step is logged: the question it asked, the answer, the noise, the budget spent.", 5)
        rec.go("/cockpit/supply-chain")
        rec.caption("The supply chain view shows the same story: stock leaving its channel, in red.", 6)

        # ---- Scenario 4: privacy by design
        rec.card("s4", 3.5)
        rec.go("/cockpit/console")
        page.get_by_label("Question").fill("Which individual buyers at Store B bought serial X123, with their age and gender?")
        rec.caption("An analyst asks for individual buyers.", 3)
        rec.click(page.get_by_role("button", name=re.compile("Plan queries")))
        rec.wait(3)
        rec.caption("It can't list individuals: the question becomes an aggregate, privacy-protected count.", 5)
        run = page.get_by_role("button", name=re.compile(r"^Run \d+ quer"))
        if run.count():
            rec.click(run.first)
            rec.wait(3)
            page.mouse.wheel(0, 600)
            rec.caption("Answers come back with noise and ±95% intervals, small groups hidden, each query spending budget.", 6)

        # ---- Onboarding and close
        rec.card("onboard", 7)
        rec.card("close", 7)

        video = page.video.path() if page.video else None
        ctx.close()
        browser.close()
    with open(os.path.join(OUT, "marks.json"), "w") as f:
        json.dump({"video": str(video), "marks": rec.marks}, f, indent=1)
    print("video:", video)


if __name__ == "__main__":
    main()
