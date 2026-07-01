from playwright.sync_api import sync_playwright

print("Uruchamianie Playwright...")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False
    )

    page = browser.new_page()

    page.goto(
        "https://www.google.com",
        wait_until="networkidle"
    )

    print("Tytuł strony:")
    print(page.title())

    input("Naciśnij ENTER aby zamknąć przeglądarkę...")

    browser.close()

print("Koniec programu")
