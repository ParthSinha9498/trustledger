"""Pre-flight check before marking a PR ready: reproduces what reviewers keep catching.

    uv run --with playwright python -m playwright install chromium     # once
    uv run --with playwright python e2e/preflight.py --start --build    # full run (spawns next dev on :3300)
    uv run --with playwright python e2e/preflight.py --start --quick    # 390 + 1440, light only
    uv run --with playwright python e2e/preflight.py --base-url http://localhost:3000 --api http://localhost:8000

Needs a running API (default http://localhost:8100, the tl-demo stack). It only sends GETs, so any stack works.
Checks:
  build     --build: `npm run build` passes; prerendered pages contain the top nav and don't bail out to client rendering
  wording   banned claims in web/app, web/components, README.md, docs/ (escape a line with `preflight-allow`)
  render    each page x size x colour scheme loads with content (full-page screenshot in OUT)
  overflow  no sideways page scroll; lists up to 5 elements past the right edge
  console   no console errors, page errors or React hydration warnings
  menu      at 390: the mobile menu toggle (aria-controls) opens, and Escape closes it
Writes OUT/report.md, OUT/report.json and the screenshots. Exit status 1 on any FAIL.
"""
import argparse, json, os, re, signal, socket, subprocess, sys, time, urllib.request
from playwright.sync_api import Page, sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
PAGES = ["/", "/pos", "/privacy", "/story", "/cockpit", "/cockpit/console", "/cockpit/supply-chain", "case"]
SIZES = [(1440, 900), (390, 844)]
SCHEMES = ["light", "dark"]
PRERENDERED = ["index", "privacy", "pos", "cockpit", "story"]
NO_NAV = {"story"}  # Nav returns null on /story by design
BANNED = ["unlimited", "zero-knowledge", "zero knowledge", "nothing leaked", "@trustledger/sdk", "via APIMatic", "±95%"]
LINT_DIRS = ["web/app", "web/components", "docs"]
LINT_FILES = ["README.md"]
TEXT_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".css", ".md", ".mdx", ".html", ".json", ".txt", ".yml", ".yaml"}

results: list[dict] = []


def add(check: str, result: str, detail: str = "", page: str = "", size: str = "", scheme: str = "") -> None:
    results.append({"check": check, "page": page, "size": size, "scheme": scheme, "result": result, "detail": detail})
    if result in ("FAIL", "WARN"):
        print(f"  {result} {check} {page} {size} {scheme} {detail}".rstrip(), flush=True)


# ---------------------------------------------------------------- build

def check_build(api: str, out: str) -> None:
    print("build: npm run build", flush=True)
    tsinfo = os.path.join(WEB, "tsconfig.tsbuildinfo")
    had_tsinfo = os.path.exists(tsinfo)
    t0 = time.monotonic()
    with open(os.path.join(out, "build.log"), "w") as log:
        rc = subprocess.run(["npm", "run", "build"], cwd=WEB, stdout=log, stderr=subprocess.STDOUT,
                            env={**os.environ, "NEXT_PUBLIC_API_URL": api}).returncode
    if not had_tsinfo and os.path.exists(tsinfo) and subprocess.run(
            ["git", "check-ignore", "-q", tsinfo], cwd=ROOT).returncode != 0:
        os.remove(tsinfo)
    took = f"{time.monotonic() - t0:.0f}s"
    if rc != 0:
        tail = open(os.path.join(out, "build.log")).read().strip().splitlines()[-15:]
        add("build", "FAIL", f"exit {rc} after {took}; see build.log: " + " | ".join(tail)[-600:])
        return
    add("build", "PASS", f"built in {took}")
    for name in PRERENDERED:
        path = os.path.join(WEB, ".next", "server", "app", f"{name}.html")
        page = "/" if name == "index" else f"/{name}"
        if not os.path.exists(path):
            if name != "story":
                add("prerender", "WARN", "no prerendered HTML (dynamic route?)", page)
            continue
        html = open(path, encoding="utf-8").read()
        navs, bails = html.count('class="topnav"'), html.count("BAILOUT_TO_CLIENT_SIDE_RENDERING")
        if name in NO_NAV:
            add("prerender-nav", "PASS", f"topnav x{navs} (hidden on this page by design)", page)
        else:
            add("prerender-nav", "PASS" if navs >= 1 else "FAIL", f'class="topnav" x{navs}', page)
        if bails:
            add("prerender-bailout", "WARN" if name == "story" else "FAIL",
                f"BAILOUT_TO_CLIENT_SIDE_RENDERING x{bails}" + (" (story may bail out itself)" if name == "story" else ""),
                page)
        else:
            add("prerender-bailout", "PASS", "", page)


# ---------------------------------------------------------------- wording

def check_wording() -> None:
    pattern = re.compile("|".join(re.escape(w) for w in BANNED), re.IGNORECASE)
    files = [os.path.join(ROOT, f) for f in LINT_FILES]
    for d in LINT_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, d)):
            dirnames[:] = [x for x in dirnames if x not in ("node_modules", ".next")]
            files += [os.path.join(dirpath, f) for f in filenames if os.path.splitext(f)[1] in TEXT_EXT]
    hits = 0
    for path in sorted(files):
        try:
            lines = open(path, encoding="utf-8").read().splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for n, line in enumerate(lines, 1):
            m = pattern.search(line)
            if m and "preflight-allow" not in line:
                hits += 1
                add("wording", "FAIL", f'{os.path.relpath(path, ROOT)}:{n} "{m.group(0)}": {line.strip()[:120]}')
    if not hits:
        add("wording", "PASS", f"{len(files)} files, {len(BANNED)} phrases")


# ---------------------------------------------------------------- browser

# Elements whose right edge is past the viewport, outermost first. Skips hidden elements and anything inside a
# container that scrolls or clips horizontally (grids, charts, carousels), since those don't move the page.
OVERFLOW_JS = """() => {
  const vw = document.documentElement.clientWidth, out = [];
  const clips = el => el !== document.body && el !== document.documentElement &&
    ['auto', 'scroll', 'hidden', 'clip'].includes(getComputedStyle(el).overflowX);
  const walk = (el, depth) => {
    for (const c of el.children) {
      if (out.length >= 5) return;
      if (!c.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
      const r = c.getBoundingClientRect();
      if (r.width > 0 && r.height > 0 && r.right > vw + 1) {
        const cls = typeof c.className === 'string' ? c.className.trim().split(/\\s+/).slice(0, 2).join('.') : '';
        const text = (c.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 40);
        out.push(`${c.tagName.toLowerCase()}${c.id ? '#' + c.id : ''}${cls ? '.' + cls : ''}` +
                 ` right=${Math.round(r.right)}${text ? ` "${text}"` : ''}`);
        continue;
      }
      if (!clips(c)) walk(c, depth + 1);
    }
  };
  walk(document.body, 0);
  return { scrollWidth: document.documentElement.scrollWidth, clientWidth: vw, offenders: out,
           text: (document.body.innerText || '').trim().length };
}"""


def slug(path: str) -> str:
    return "home" if path == "/" else path.strip("/").replace("/", "-")


def first_case(api: str) -> str | None:
    with urllib.request.urlopen(api + "/cases", timeout=10) as r:
        cases = json.load(r)
    return cases[0]["case_id"] if cases else None


def check_page(browser, base: str, path: str, name: str, w: int, h: int, scheme: str, out: str) -> bool:
    """Returns True if the page has a mobile menu toggle (aria-controls)."""
    size, tag = f"{w}x{h}", f"{name}-{w}-{scheme}"
    ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
    page: Page = ctx.new_page()
    errors, hydration = [], []

    def on_console(msg) -> None:
        text = msg.text.strip().replace("\n", " ")
        if "hydrat" in text.lower() and msg.type in ("error", "warning"):
            hydration.append(text[:200])
        elif msg.type == "error":
            errors.append(text[:200])

    page.on("console", on_console)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {str(e)[:200]}"))
    has_menu = False
    try:
        resp = page.goto(base + path, wait_until="load", timeout=90000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            add("render", "WARN", "network not idle after 15s", name, size, scheme)
        page.wait_for_timeout(1200)
        m = page.evaluate(OVERFLOW_JS)
        screenshot_full(page, os.path.join(out, f"{tag}.png"), w, h)
        status = resp.status if resp else 0
        if status >= 400 or m["text"] < 20:
            add("render", "FAIL", f"HTTP {status}, {m['text']} chars of text", name, size, scheme)
        else:
            add("render", "PASS", f"{tag}.png", name, size, scheme)
        extra = m["scrollWidth"] - m["clientWidth"]
        offenders = "; ".join(m["offenders"])
        if extra > 1:
            add("overflow", "FAIL", f"scrollWidth {m['scrollWidth']} > {m['clientWidth']}: {offenders}", name, size, scheme)
        elif m["offenders"]:
            add("overflow", "WARN", f"clipped past the right edge: {offenders}", name, size, scheme)
        else:
            add("overflow", "PASS", "", name, size, scheme)
        if w < 600:
            has_menu = check_menu(page, tag, name, size, scheme, out)
    except Exception as e:
        add("render", "FAIL", f"{type(e).__name__}: {str(e).splitlines()[0][:200]}", name, size, scheme)
    finally:
        add("console", "FAIL" if errors else "PASS", " | ".join(dict.fromkeys(errors))[:600], name, size, scheme)
        add("hydration", "FAIL" if hydration else "PASS", " | ".join(dict.fromkeys(hydration))[:600], name, size, scheme)
        ctx.close()
    return has_menu


def screenshot_full(page: Page, path: str, w: int, h: int) -> None:
    """Full-page screenshot via a viewport as tall as the page: Playwright's full_page capture leaves AG Grid and
    Bryntum below the fold blank, which looks like a broken page in review."""
    page.add_style_tag(content="nextjs-portal { display: none !important; }")  # the dev-tools badge covers content
    tall = page.evaluate("document.documentElement.scrollHeight")
    if tall > h:
        page.set_viewport_size({"width": w, "height": tall})
        page.wait_for_timeout(800)
    page.screenshot(path=path, full_page=True)
    page.set_viewport_size({"width": w, "height": h})
    page.wait_for_timeout(300)


def check_menu(page: Page, tag: str, name: str, size: str, scheme: str, out: str) -> bool:
    # Light DOM only: Playwright's CSS pierces shadow roots and would find the Next.js dev-tools button.
    found = page.evaluate("""() => {
      const t = [...document.querySelectorAll('button[aria-controls], [role=button][aria-controls]')]
        .find(el => el.checkVisibility({ visibilityProperty: true }));
      if (t) t.setAttribute('data-preflight-toggle', '1');
      return !!t;
    }""")
    if not found:
        return False
    toggle = page.locator("[data-preflight-toggle='1']")
    target = page.locator(f"[id='{toggle.get_attribute('aria-controls')}']")
    toggle.click()
    page.wait_for_timeout(500)
    page.screenshot(path=os.path.join(out, f"{tag}-menu.png"))
    opened = toggle.get_attribute("aria-expanded") == "true" or (target.count() and target.first.is_visible())
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    closed = toggle.get_attribute("aria-expanded") != "true" and not (target.count() and target.first.is_visible())
    if opened and closed:
        add("menu", "PASS", f"{tag}-menu.png", name, size, scheme)
    else:
        add("menu", "WARN", f"opened={bool(opened)} closed_by_escape={bool(closed)} ({tag}-menu.png)", name, size, scheme)
    return True


def check_browser(base: str, api: str, pages: list[str], sizes, schemes, out: str) -> None:
    targets = []
    for p in pages:
        if p == "case":
            try:
                cid = first_case(api)
            except Exception as e:
                add("render", "FAIL", f"GET {api}/cases failed: {e}", "case")
                continue
            if cid is None:
                add("render", "SKIP", f"no cases at {api}/cases", "case")
                continue
            targets.append((f"/cockpit/cases/{cid}", "case"))
        else:
            targets.append((p, slug(p)))
    no_menu = []
    with sync_playwright() as pw:
        # The API's CORS only allows its own web origin; the page under test runs on another port.
        browser = pw.chromium.launch(args=["--disable-web-security"])
        try:
            for path, name in targets:
                print(f"browser: {path}", flush=True)
                for w, h in sizes:
                    for scheme in schemes:
                        if not check_page(browser, base, path, name, w, h, scheme, out) and w < 600:
                            no_menu.append(name)
        finally:
            browser.close()
    if no_menu:
        add("menu", "SKIP", "no aria-controls toggle on: " + ", ".join(dict.fromkeys(no_menu)))


# ---------------------------------------------------------------- dev server

def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_dev(port: int, api: str, out: str) -> subprocess.Popen:
    if port_open(port):
        sys.exit(f"port {port} is already in use; stop that server or pass --base-url")
    print(f"dev: npx next dev -p {port} (log: {out}/next-dev.log)", flush=True)
    log = open(os.path.join(out, "next-dev.log"), "w")
    proc = subprocess.Popen(["npx", "next", "dev", "-p", str(port)], cwd=WEB, stdout=log, stderr=subprocess.STDOUT,
                            env={**os.environ, "NEXT_PUBLIC_API_URL": api}, start_new_session=True)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"next dev exited with {proc.returncode}; see {out}/next-dev.log")
        try:
            urllib.request.urlopen(f"http://localhost:{port}/", timeout=60).close()
            return proc
        except Exception:
            time.sleep(1)
    raise RuntimeError("next dev did not answer within 120s")


def stop_dev(proc: subprocess.Popen) -> None:
    for sig, wait in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
            proc.wait(timeout=wait)
            return
        except ProcessLookupError:
            return
        except subprocess.TimeoutExpired:
            continue


def warm_up(base: str, pages: list[str]) -> None:
    """Compile each route once so the first measured load isn't a dev-server compile."""
    for p in pages:
        if p != "case":
            try:
                urllib.request.urlopen(base + p, timeout=120).close()
            except Exception:
                pass


# ---------------------------------------------------------------- report

def report(out: str, args, took: float) -> int:
    counts = {k: sum(r["result"] == k for r in results) for k in ("FAIL", "WARN", "PASS", "SKIP")}
    order = {"FAIL": 0, "WARN": 1, "SKIP": 2, "PASS": 3}
    head = "| check | page | size | scheme | result | detail |\n|---|---|---|---|---|---|\n"
    row = lambda r: "| " + " | ".join(str(r[k]).replace("|", "\\|") for k in
                                      ("check", "page", "size", "scheme", "result", "detail")) + " |\n"
    ranked = sorted(results, key=lambda r: order[r["result"]])
    summary = (f"**Pre-flight: {'FAIL' if counts['FAIL'] else 'PASS'}**: {counts['FAIL']} fail, {counts['WARN']} warn, "
               f"{counts['PASS']} pass, {counts['SKIP']} skip in {took:.0f}s "
               f"(git {git_rev()}, {'quick' if args.quick else 'full'}{', build' if args.build else ''})\n\n")
    with open(os.path.join(out, "report.md"), "w") as f:
        f.write(summary + head + "".join(row(r) for r in ranked))
    with open(os.path.join(out, "report.json"), "w") as f:
        json.dump({"git": git_rev(), "seconds": round(took, 1), "counts": counts, "args": vars(args),
                   "results": results}, f, indent=2)
    shown = [r for r in ranked if r["result"] != "PASS"]
    passed = {}
    for r in results:
        if r["result"] == "PASS":
            passed[r["check"]] = passed.get(r["check"], 0) + 1
    print("\n" + summary + head + "".join(row(r) for r in shown), end="")
    print("| " + ", ".join(f"{k} x{v}" for k, v in passed.items()) + " | | | | PASS | |\n")
    print(f"Full table: {out}/report.md · screenshots in {out}/")
    return 1 if counts["FAIL"] else 0


def git_rev() -> str:
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    return r.stdout.strip() + ("+dirty" if dirty else "")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=3300)
    ap.add_argument("--api", default="http://localhost:8100")
    ap.add_argument("--start", action="store_true", help="spawn `npx next dev -p PORT` in web/ and stop it at the end")
    ap.add_argument("--base-url", help="test an already-running web server instead")
    ap.add_argument("--build", action="store_true", help="run `npm run build` in web/ first")
    ap.add_argument("--out", default=f"/tmp/preflight-{time.strftime('%Y%m%d-%H%M%S')}")
    ap.add_argument("--pages", help=f"comma-separated paths ('case' = first case); default {','.join(PAGES)}")
    ap.add_argument("--quick", action="store_true", help="390 light + 1440 light only")
    args = ap.parse_args()
    if not args.start and not args.base_url:
        ap.error("pass --start or --base-url")
    args.api = args.api.rstrip("/")
    os.makedirs(args.out, exist_ok=True)
    pages = [p.strip() for p in args.pages.split(",")] if args.pages else PAGES
    schemes = ["light"] if args.quick else SCHEMES
    base = (args.base_url or f"http://localhost:{args.port}").rstrip("/")

    t0, proc = time.monotonic(), None
    try:
        if args.build:
            check_build(args.api, args.out)
        print("wording lint", flush=True)
        check_wording()
        if args.start:
            proc = start_dev(args.port, args.api, args.out)
            warm_up(base, pages)
        check_browser(base, args.api, pages, SIZES, schemes, args.out)
    except Exception as e:
        add("preflight", "FAIL", f"{type(e).__name__}: {e}")
    finally:
        if proc is not None:
            stop_dev(proc)
    sys.exit(report(args.out, args, time.monotonic() - t0))


if __name__ == "__main__":
    main()
