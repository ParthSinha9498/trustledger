import base64
import json
import os
import time
from playwright.sync_api import sync_playwright

DOCS_MEDIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "media")
os.makedirs(DOCS_MEDIA, exist_ok=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        hide_devtools = "nextjs-portal, [data-nextjs-dev-tools-button], #__next-build-watcher, [data-nextjs-toast] { display: none !important; }"

        # 1. 01_pos_verified.png: Store A verified
        print("Capturing 01_pos_verified...")
        page.goto("http://localhost:3000/pos")
        page.add_style_tag(content=hide_devtools)
        page.wait_for_selector("button:has-text('Store A')")
        page.click("button:has-text('Store A')")
        page.fill("#serial", "X123")
        page.click("button:has-text('Verify and check out')")
        page.wait_for_selector("text=Brand verified", timeout=15000)
        # Wait for PayPal container / buttons to load to avoid "Loading PayPal..."
        try:
            page.wait_for_selector("iframe, [class*='paypal-button'], text=Open the pay screen", timeout=6000)
        except Exception:
            pass
        time.sleep(2.5)
        pos_a_path = os.path.join(DOCS_MEDIA, "01_pos_verified.png")
        page.screenshot(path=pos_a_path)

        # 2. 02_pos_blocked.png: Store B blocked & retrieve dynamic case_id
        print("Capturing 02_pos_blocked...")
        page.click("button:has-text('Store B')")
        page.fill("#serial", "X123")
        page.click("button:has-text('Verify and check out')")
        page.wait_for_selector("text=Not verified", timeout=15000)
        time.sleep(1.2)
        pos_b_path = os.path.join(DOCS_MEDIA, "02_pos_blocked.png")
        page.screenshot(path=pos_b_path)

        # Dynamically discover case_id from the blocked verdict link
        case_id = None
        case_link = page.query_selector("a[href*='/cockpit/cases/']")
        if case_link:
            href = case_link.get_attribute("href")
            case_id = href.split("/cockpit/cases/")[-1]
            print(f"Discovered case_id: {case_id}")

        # 3. 03_compare.png: Side-by-side split screen with no letterbox bars
        print("Capturing 03_compare...")
        with open(pos_a_path, "rb") as f:
            b64_a = base64.b64encode(f.read()).decode("utf-8")
        with open(pos_b_path, "rb") as f:
            b64_b = base64.b64encode(f.read()).decode("utf-8")

        compare_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ background: #0f172a; display: flex; width: 1280px; height: 720px; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
            .split {{ flex: 1; height: 100%; border-right: 2px solid #334155; position: relative; overflow: hidden; display: flex; }}
            .split:last-child {{ border-right: none; }}
            img {{ width: 100%; height: 100%; object-fit: cover; object-position: 50% 12%; }}
            .badge {{ position: absolute; top: 20px; left: 20px; padding: 10px 18px; border-radius: 8px; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; box-shadow: 0 4px 16px rgba(0,0,0,0.6); z-index: 10; }}
            .badge-verified {{ background: #10b981; color: #fff; }}
            .badge-blocked {{ background: #ef4444; color: #fff; }}
          </style>
        </head>
        <body>
          <div class="split">
            <div class="badge badge-verified">Store A · Genuine Serial (PayPal Order Created)</div>
            <img src="data:image/png;base64,{b64_a}">
          </div>
          <div class="split">
            <div class="badge badge-blocked">Store B · Cloned Serial (Payment Blocked)</div>
            <img src="data:image/png;base64,{b64_b}">
          </div>
        </body>
        </html>
        """
        split_page = context.new_page()
        split_page.set_content(compare_html)
        time.sleep(0.5)
        split_page.screenshot(path=os.path.join(DOCS_MEDIA, "03_compare.png"))
        split_page.close()

        # 4. 04_cockpit_case.png: Investigation case with agent steps & citations
        print("Capturing 04_cockpit_case...")
        if case_id:
            page.goto(f"http://localhost:3000/cockpit/cases/{case_id}")
        else:
            page.goto("http://localhost:3000/cockpit")
            time.sleep(1.0)
            cl = page.query_selector("a[href*='/cockpit/cases/']")
            if cl:
                cl.click()
        page.add_style_tag(content=hide_devtools)
        time.sleep(2.0)
        page.screenshot(path=os.path.join(DOCS_MEDIA, "04_cockpit_case.png"))

        # 5. 05_console_aggregate.png: DP Console with PayPal query, results table, & ±CI
        print("Capturing 05_console_aggregate...")
        page.goto("http://localhost:3000/cockpit/console")
        page.add_style_tag(content=hide_devtools)
        time.sleep(1.5)
        # Click the PayPal demographic question
        pp_btn = page.wait_for_selector("button:has-text('buyers of NMB-P8-128')", timeout=10000)
        pp_btn.click()
        # Wait for planning to complete and Run button to become active
        run_btn = page.wait_for_selector("button:has-text('Run')", timeout=15000)
        run_btn.click()
        # Wait for results table with CI or noise metadata
        try:
            page.wait_for_selector("text=Results, text=±", timeout=12000)
        except Exception:
            pass
        time.sleep(2.0)
        page.screenshot(path=os.path.join(DOCS_MEDIA, "05_console_aggregate.png"))

        # 6. 06_supply_chain.png: Bryntum Supply Chain Gantt/Scheduler
        print("Capturing 06_supply_chain...")
        page.goto("http://localhost:3000/cockpit/supply-chain")
        page.add_style_tag(content=hide_devtools)
        time.sleep(3.0)
        page.screenshot(path=os.path.join(DOCS_MEDIA, "06_supply_chain.png"))

        # 7. 07_story_hook.png: Story Card Hook
        print("Capturing 07_story_hook...")
        page.goto("http://localhost:3000/story?card=hook")
        page.add_style_tag(content=hide_devtools)
        page.wait_for_selector("body[data-ready='1']", timeout=5000)
        time.sleep(0.5)
        page.screenshot(path=os.path.join(DOCS_MEDIA, "07_story_hook.png"))

        print("All screenshots captured successfully to docs/media/!")
        browser.close()

if __name__ == "__main__":
    main()
