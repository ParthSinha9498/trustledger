import os
import time
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "e2e", "out", "story")
os.makedirs(OUT, exist_ok=True)

CARDS = ["hook", "problem", "gap", "idea", "s1", "s2", "s3", "s4", "redteam", "s5", "terminal", "code", "onboard", "close"]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})

        # Capture each card
        for cid in CARDS:
            url = f"http://localhost:3000/story?card={cid}"
            print(f"Capturing {cid} from {url}...")
            page.goto(url)
            page.add_style_tag(content="nextjs-portal, [data-nextjs-dev-tools-button], #__next-build-watcher, [data-nextjs-toast] { display: none !important; }")
            page.wait_for_selector("body[data-ready='1']", timeout=5000)
            time.sleep(0.3)  # brief settle
            dest = os.path.join(OUT, f"{cid}.png")
            page.screenshot(path=dest)
            print(f"Saved {dest}")

        # Capture index
        print("Capturing story index...")
        page.goto("http://localhost:3000/story")
        time.sleep(0.5)
        dest = os.path.join(OUT, "index.png")
        page.screenshot(path=dest)
        print(f"Saved {dest}")

        browser.close()

if __name__ == "__main__":
    main()
