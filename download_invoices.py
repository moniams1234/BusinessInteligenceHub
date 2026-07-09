import argparse
import sys
from datetime import datetime
from pathlib import Path

from ensure_playwright import ensure_chromium_installed

ensure_chromium_installed()

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


BASE_DIR = Path(__file__).resolve().parent
BASE_URL = "https://myprint.graphicwest.biz/system"
LIST_URL = f"{BASE_URL}/finance_customer_invoices.php?action=list"
DOWNLOAD_DIR = BASE_DIR / "downloads"
LOGIN_STATE = BASE_DIR / "myprint_login.json"
EXPORT_SELECTOR = (
    'a[href*="finance_customer_invoices_export.php"], '
    'a:has-text("XLS"), button:has-text("XLS")'
)


def download_invoice(headless: bool = True) -> Path:
    """Download the latest MyPrint sales invoice export and return its path."""
    if not LOGIN_STATE.exists():
        raise FileNotFoundError(
            "Brak pliku myprint_login.json. Najpierw uruchom save_login.py."
        )

    DOWNLOAD_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = DOWNLOAD_DIR / f"myprint_faktury_sprzedazy_{timestamp}.xls"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            try:
                context = browser.new_context(
                    storage_state=str(LOGIN_STATE), accept_downloads=True
                )
                page = context.new_page()
                page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60_000)

                if page.locator('input[type="password"]').count() > 0:
                    raise RuntimeError(
                        "Sesja MyPrint wygasła. Uruchom save_login.py i zaloguj się ponownie."
                    )

                xls_link = page.locator(EXPORT_SELECTOR).first
                try:
                    xls_link.wait_for(state="visible", timeout=15_000)
                except PlaywrightTimeoutError as exc:
                    current_url = page.url.lower()
                    if "login" in current_url or "index.php" in current_url:
                        raise RuntimeError(
                            "Sesja MyPrint wygasła. Uruchom save_login.py i zaloguj się ponownie."
                        ) from exc
                    raise RuntimeError(
                        "MyPrint nie wyświetlił przycisku XLS. Sesja mogła wygasnąć "
                        f"albo zmienił się widok strony (adres: {page.url})."
                    ) from exc

                with page.expect_download(timeout=60_000) as download_info:
                    xls_link.click(timeout=15_000)
                download_info.value.save_as(str(output_file))
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise RuntimeError(
            "MyPrint nie odpowiedział na czas. Uruchom save_login.py i odnów sesję."
        ) from exc

    return output_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Pobierz faktury sprzedaży z MyPrint.")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Pokaż okno przeglądarki (domyślnie pobieranie działa w tle).",
    )
    args = parser.parse_args()
    try:
        output_file = download_invoice(headless=not args.headed)
    except Exception as exc:
        print(f"Błąd pobierania: {exc}", file=sys.stderr)
        return 1

    print(f"Pobrano plik: {output_file.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
