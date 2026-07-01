import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
STOCK_URL = "https://myprint.graphicwest.biz/system/material_stat_daystockPart.php?action=menu"
DOWNLOAD_DIR = BASE_DIR / "downloads"
LOGIN_STATE = BASE_DIR / "myprint_login.json"

_EXPORT_SELECTOR = (
    "button:has-text('Eksport'), "
    "a:has-text('Eksport'), "
    "button:has-text('XLS'), "
    "a:has-text('XLS')"
)
_FILTER_BTN_SELECTOR = (
    "button:has-text('filtruj'), "
    "input[value='filtruj'], "
    "button:has-text('Filtruj')"
)


def _check_session(page) -> None:
    if page.locator('input[type="password"]').count() > 0:
        raise RuntimeError(
            "Sesja MyPrint wygasła. Uruchom save_login.py i zaloguj się ponownie."
        )


def _select_type_filter(page, value: str) -> None:
    """Set the Typ surowca dropdown to the given value."""
    # Try standard HTML select first
    for sel in page.locator("select").all():
        for opt in sel.locator("option").all():
            if value.lower() in (opt.text_content() or "").lower():
                sel.select_option(label=opt.text_content())
                return
    # Fallback: Bootstrap multiselect — click the button, then the option
    dropdown_btn = page.locator(f"button:has-text('{value}'), .multiselect__option:has-text('{value}')").first
    if dropdown_btn.is_visible():
        dropdown_btn.click()
        return
    raise RuntimeError(
        f"Nie znaleziono filtra Typ surowca dla wartości: '{value}'. "
        "Sprawdź selektory w _select_type_filter()."
    )


def _set_analysis_date(page, analysis_date: date | None) -> None:
    if analysis_date is None:
        return

    date_values = [
        analysis_date.isoformat(),
        analysis_date.strftime("%d.%m.%Y"),
        analysis_date.strftime("%Y/%m/%d"),
        analysis_date.strftime("%d/%m/%Y"),
    ]
    selectors = [
        "input[type='date']",
        "input[name*='date' i]",
        "input[id*='date' i]",
        "input[name*='data' i]",
        "input[id*='data' i]",
        "input[name*='day' i]",
        "input[id*='day' i]",
    ]

    for selector in selectors:
        locator = page.locator(selector)
        for idx in range(locator.count()):
            field = locator.nth(idx)
            if not field.is_visible():
                continue
            for value in date_values:
                try:
                    field.fill(value)
                    return
                except Exception:
                    continue

    for label in ["Data", "Data analizy", "Dzień", "Day", "Date"]:
        field = page.get_by_label(label, exact=False)
        if field.count() == 0:
            continue
        for value in date_values:
            try:
                field.first.fill(value)
                return
            except Exception:
                continue

    if analysis_date != date.today():
        raise RuntimeError(
            "Nie znaleziono pola daty w MyPrint. Nie można pobrać stocku "
            f"na dzień {analysis_date.isoformat()}."
        )


def _click_filter(page) -> None:
    btn = page.locator(_FILTER_BTN_SELECTOR).first
    btn.wait_for(state="visible", timeout=10_000)
    btn.click()
    page.wait_for_load_state("domcontentloaded", timeout=30_000)


def _download_one_type(
    page,
    type_label: str,
    output_path: Path,
    analysis_date: date | None = None,
) -> Path:
    page.goto(STOCK_URL, wait_until="domcontentloaded", timeout=60_000)
    _check_session(page)
    _set_analysis_date(page, analysis_date)
    _select_type_filter(page, type_label)
    _click_filter(page)
    export_btn = page.locator(_EXPORT_SELECTOR).first
    export_btn.wait_for(state="visible", timeout=15_000)
    with page.expect_download(timeout=60_000) as dl_info:
        export_btn.click(timeout=15_000)
    dl_info.value.save_as(str(output_path))
    return output_path


def download_stock(
    headless: bool = True,
    analysis_date: date | None = None,
) -> tuple[Path, Path]:
    if not LOGIN_STATE.exists():
        raise FileNotFoundError(
            "Brak pliku myprint_login.json. Najpierw uruchom save_login.py."
        )
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    date_part = analysis_date.isoformat() if analysis_date else "current"
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path_komp = DOWNLOAD_DIR / f"stock_komponenty_{date_part}_{ts}.xlsx"
    path_mag = DOWNLOAD_DIR / f"stock_magazynowy_{date_part}_{ts}.xlsx"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            try:
                ctx = browser.new_context(
                    storage_state=str(LOGIN_STATE),
                    accept_downloads=True,
                )
                page = ctx.new_page()
                _download_one_type(page, "Komponenty", path_komp, analysis_date)
                _download_one_type(page, "Magazynowy / Stock", path_mag, analysis_date)
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise RuntimeError(
            "MyPrint nie odpowiedział na czas. Odnów sesję przez save_login.py."
        ) from exc
    return path_komp, path_mag


def main() -> int:
    parser = argparse.ArgumentParser(description="Pobierz raporty stock z MyPrint.")
    parser.add_argument("--headed", action="store_true", help="Pokaż okno przeglądarki.")
    parser.add_argument("--date", help="Data stocku w formacie YYYY-MM-DD.")
    args = parser.parse_args()
    try:
        selected_date = date.fromisoformat(args.date) if args.date else None
        path_komp, path_mag = download_stock(
            headless=not args.headed,
            analysis_date=selected_date,
        )
    except Exception as exc:
        print(f"Błąd pobierania: {exc}", file=sys.stderr)
        return 1
    print(f"Pobrano Komponenty:  {path_komp}")
    print(f"Pobrano Magazynowy:  {path_mag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
