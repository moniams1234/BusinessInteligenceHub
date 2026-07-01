import sys
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    pg = br.new_page(viewport={"width": 1400, "height": 900})
    pg.goto("http://localhost:8501/Otiocon_Stock", timeout=30000)
    pg.wait_for_load_state("networkidle", timeout=20000)
    time.sleep(7)
    # Scroll to bottom
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)
    pg.screenshot(path="screenshot_bottom.png")
    # Check buttons at bottom
    buttons = pg.evaluate("""
        () => Array.from(document.querySelectorAll('button')).map(b => b.innerText.trim()).filter(t => t.length > 0)
    """)
    print("All buttons:", buttons[-6:])
    br.close()
