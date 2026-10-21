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
import argparse, base64, html, json, os, re, socket, subprocess, time, urllib.request
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
                "up to 2.3% of world trade · up to 4.7% of EU imports · smartphones: 12.9% of sales (EUR 45.3B, 2015)",
                "OECD / EUIPO, Mapping Global Trade in Fakes 2025 (2021 data)"],
    "phones": ["12.9% of legitimate smartphone sales lost to counterfeits", "≈ EUR 45.3 billion",
               "EUIPO / ITU, smartphone sector study (2015 data)"],
    "gap": ["Verification exists. Nobody uses it.", "Optional · separate from paying · different for every brand"],
    "idea": ["Make authenticity a condition of payment.", "Scan → brand verifies → PayPal payment. Not verified → no payment."],
    "s1": ["Scenario 1", "A genuine phone at an authorized store"],
    "s2": ["Scenario 2", "The same serial at a store outside the supply chain"],
    "s3": ["Scenario 3", "The brand investigates"],
    "s4": ["Scenario 4", "Privacy by design"],
    "s5": ["Scenario 5", "An AI shopping agent checks before it pays"],
    "redteam": ["220 of 220 re-identification attempts blocked",
                "Best guesses were right 23% of the time, no better than chance",
                "Scripted battery: small cells, differencing, membership, cross-node linkage, averaging, budget probing"],
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


HERE = os.path.dirname(os.path.abspath(__file__))
MCP_DIR = os.path.join(HERE, "..", "mcp")


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
        + tile(b_png, "Store B · same X123 · no PayPal order", "#ff8a80") + "</body>")
    rec.wait(hold)


def pay_in_sandbox(rec: Recorder, checkout_id: str) -> None:
    """Buyer approves in PayPal's own window; the page captures and moves to the receipt."""
    page = rec.page
    rec.go(f"/pay/{checkout_id}")
    page.wait_for_selector("paypal-button", state="visible", timeout=30000)
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
    popup_video = pop.video.path() if pop.video else None
    try:
        pop.wait_for_event("close", timeout=30000)
    except Exception:
        pass
    rec.mark("popup_close", str(popup_video or ""))
    page.wait_for_url(re.compile(r"/receipt/"), timeout=60000)


def mcp_agent_lines(brand_url: str, token: str, port: int = 3333) -> list[str]:
    """Start the brand-verification MCP server, run the demo agent against it, return its real output."""
    env = os.environ | {"API_BASE_URL": brand_url, "API_KEY_NODETOKEN": token, "PORT": str(port)}
    srv = subprocess.Popen(["node", "build/index.js", "--transport=streamable-http"],
                           cwd=os.path.join(MCP_DIR, "brand-verification"), env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.2)
        out = subprocess.run(["node", "demo_agent_call.mjs", "--store", "store_b", "--serial", SERIAL,
                              "--sku", "NMB-P8-128"], cwd=MCP_DIR, capture_output=True, text=True, timeout=60,
                             env=os.environ | {"MCP_URL": f"http://127.0.0.1:{port}/mcp"})
        lines = [l for l in out.stdout.splitlines()]
        # The video shows the agent's reasoning, not the raw JSON dump at the end.
        return lines[: next((i for i, l in enumerate(lines) if l.startswith("Raw MCP")), len(lines))]
    finally:
        srv.terminate()


def terminal_scene(rec: Recorder, lines: list[str], hold: float) -> None:
    rec.mark("scene", "terminal")
    page = rec.page
    r = page.goto(f"{rec.web}/story?card=terminal")
    if r is not None and r.ok and page.evaluate("typeof window.typeLines === 'function'"):
        page.evaluate("lines => window.typeLines(lines)", lines)
        try:
            page.wait_for_selector("body[data-ready='1']", timeout=30000)
        except Exception:
            pass
    else:
        body = "\n".join(html.escape(l) for l in lines)
        page.set_content("<body style='margin:0;height:100vh;background:#0b1220;display:grid;place-items:center'>"
                         "<pre style='width:1100px;background:#020617;color:#e2e8f0;font:18px/1.5 ui-monospace,monospace;"
                         f"padding:28px 32px;border-radius:14px'>$ node demo_agent_call.mjs\n{body}</pre></body>")
    rec.wait(hold)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="http://localhost:3000")
    ap.add_argument("--api", default=os.environ.get("API_URL", "http://localhost:8000"))
    ap.add_argument("--brand", default=os.environ.get("BRAND_NODE_URL", "http://localhost:8001"),
                    help="brand node URL for the MCP scene")
    ap.add_argument("--brand-token", default=os.environ.get("NODE_SHARED_TOKEN", "dev-token"))
    ap.add_argument("--case-timeout", type=int, default=300, help="seconds to wait for the agent")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    mock = os.environ.get("PAYPAL_MODE", "mock") == "mock"
    # Run the MCP agent first (real output), so the scene itself only types it out.
    mcp_lines = mcp_agent_lines(args.brand, args.brand_token)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 720},
                                  record_video_dir=OUT, record_video_size={"width": 1280, "height": 720})
        ctx.add_init_script(CURSOR_JS)
        page = ctx.new_page()
        rec = Recorder(page, args.web)

        # ---- Problem and idea (storyboard: docs/demo/VOICEOVER.md)
        rec.card("hook", 4)
        rec.card("problem", 7)
        rec.card("gap", 8)
        rec.card("idea", 8)

        # ---- Scenario 1: genuine product, authorized store
        rec.card("s1", 2.5)
        rec.go("/pos")
        rec.caption("Store A: brand verifies → PayPal order created", 0.5)
        a = scan(rec, 0)
        if a.get("status") != "VERIFIED":
            raise SystemExit(f"Store A was not verified ({a.get('reason_code')}): X123 is probably already sold. "
                             "Reseed before each take (e.g. docker compose run --rm seed).")
        a_png = verdict_png(page)
        rec.ring(page.get_by_text("PayPal order created", exact=False).first)
        rec.wait(4)
        rec.unring()
        if mock:
            api_post(args.api, f"/checkout/{a['checkout_id']}/capture")
            rec.go(f"/receipt/{a['checkout_id']}")
        else:
            pay_in_sandbox(rec, a["checkout_id"])
        rec.caption("Receipt: Brand Verified", 4)

        # ---- Scenario 2: same serial, store outside the supply chain
        rec.card("s2", 2.5)
        rec.go("/pos")
        rec.caption("Store B, same serial: no PayPal order exists", 0.5)
        b = scan(rec, 1)
        b_png = verdict_png(page)
        rec.ring(page.get_by_text("Never created", exact=False).first)
        rec.wait(6)
        rec.unring()
        compare_frame(rec, a_png, b_png, 4)

        # ---- Scenario 3: the brand investigates
        rec.card("s3", 2.5)
        case_id = b.get("case_id")
        rec.go("/cockpit")
        rec.caption("AI agent investigates: aggregates only", 4)
        if case_id:
            rec.go(f"/cockpit/cases/{case_id}")
            rec.wait(3)
            rec.mark("cut_start", "agent running")
            deadline = time.time() + args.case_timeout
            while time.time() < deadline and not page.get_by_text(re.compile(r"\bcomplete\b", re.I)).count():
                rec.wait(5)
                page.reload()
                page.evaluate(CAPTION_JS, "AI agent investigates: aggregates only")
            rec.mark("cut_end", "agent done")
            rec.wait(1)
            rec.ring(page.locator("ol.findings li").first)
            rec.wait(6)
            rec.unring()
            page.mouse.wheel(0, 900)
            rec.wait(4)
        rec.go("/cockpit/supply-chain")
        rec.wait(5)

        # ---- Scenario 4: privacy by design
        rec.card("s4", 2.5)
        rec.go("/cockpit/console")
        page.get_by_label("Question").fill("Which individual buyers at Store B bought serial X123, with their age and gender?")
        rec.caption("Individuals in → private aggregate out", 2)
        rec.click(page.get_by_role("button", name=re.compile("Plan queries")))
        rec.wait(3)
        rec.ring(page.locator("p.rationale").first)
        rec.wait(4)
        rec.unring()
        run = page.get_by_role("button", name=re.compile(r"^Run \d+ quer"))
        if run.count():
            rec.click(run.first)
            rec.wait(3)
            page.mouse.wheel(0, 600)
            rec.wait(5)

        rec.card("redteam", 6)

        # ---- Scenario 5: an AI shopping agent checks before it pays (real MCP run)
        rec.card("s5", 2.5)
        terminal_scene(rec, mcp_lines, 4)

        # ---- Onboarding and close
        rec.card("onboard", 12)
        rec.card("close", 8)

        video = page.video.path() if page.video else None
        ctx.close()
        browser.close()
    with open(os.path.join(OUT, "marks.json"), "w") as f:
        json.dump({"video": str(video), "marks": rec.marks}, f, indent=1)
    print("video:", video)


if __name__ == "__main__":
    main()
