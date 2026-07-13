import os
import sys
from pathlib import Path

from ensure_playwright import ensure_chromium_installed

ensure_chromium_installed()

from playwright.sync_api import sync_playwright


BASE_DIR = Path(__file__).resolve().parent
LOGIN_STATE = BASE_DIR / "myprint_login.json"
BASE_URL = "https://myprint.graphicwest.biz/system"
LOGIN_URL = "https://myprint.graphicwest.biz/index.php"
LIST_URL = f"{BASE_URL}/finance_customer_invoices.php?action=list"
EXPORT_SELECTOR = 'a[href*="finance_customer_invoices_export.php"], a:has-text("XLS")'


def _load_credentials() -> tuple[str, str] | tuple[None, None]:
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("MYPRINT_LOGIN="):
                os.environ.setdefault("MYPRINT_LOGIN", line.split("=", 1)[1])
            elif line.startswith("MYPRINT_HASLO="):
                os.environ.setdefault("MYPRINT_HASLO", line.split("=", 1)[1])

    login = os.environ.get("MYPRINT_LOGIN", "").strip()
    haslo = os.environ.get("MYPRINT_HASLO", "").strip()
    if login and haslo:
        return login, haslo
    return None, None


def _is_on_login_page(page) -> bool:
    return (
        page.locator('input[type="password"]').count() > 0
        or "login" in page.url.lower()
        or "index.php" in page.url.lower()
    )


def _auto_login(page, login: str, haslo: str) -> None:
    """Fill and submit the MyPrint login form."""
    # Próbujemy typowych selektorów dla pól logowania
    user_selectors = [
        'input[name="login-username"]',
        'input[id="login-username"]',
        'input[name="login"]',
        'input[name="user"]',
        'input[name="username"]',
        'input[name="email"]',
        'input[type="text"]',
    ]
    pass_selectors = [
        'input[name="login-password"]',
        'input[id="login-password"]',
        'input[name="haslo"]',
        'input[name="password"]',
        'input[name="pass"]',
        'input[type="password"]',
    ]

    user_field = None
    for sel in user_selectors:
        loc = page.locator(sel).first
        if loc.count() > 0 and loc.is_visible():
            user_field = loc
            break

    pass_field = None
    for sel in pass_selectors:
        loc = page.locator(sel).first
        if loc.count() > 0 and loc.is_visible():
            pass_field = loc
            break

    if not user_field or not pass_field:
        raise RuntimeError(
            "Nie znaleziono formularza logowania. "
            "Sprawdź ręcznie adres strony i selektory pól."
        )

    user_field.fill(login)
    pass_field.fill(haslo)
    submit = page.locator('button[type="submit"], input[type="submit"], button').first
    if submit.count() > 0:
        submit.click()
    else:
        page.keyboard.press("Enter")
    page.wait_for_load_state("networkidle", timeout=30_000)


def save_session(headless: bool = True) -> None:
    """Log in to MyPrint (auto or manual) and save the session state."""
    login, haslo = _load_credentials()
    auto = login is not None

    if not auto:
        if os.environ.get("DISPLAY"):
            headless = False
            print("Brak danych w .env — otwieram przeglądarkę do ręcznego logowania.")
        else:
            raise RuntimeError(
                "Brak danych logowania do MyPrint (MYPRINT_LOGIN / MYPRINT_HASLO) "
                "i brak środowiska graficznego do logowania ręcznego (typowe na "
                "Streamlit Cloud). Dodaj MYPRINT_LOGIN i MYPRINT_HASLO w "
                "App settings -> Secrets."
            )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            context = browser.new_context()
            page = context.new_page()

            # Najpierw sprawdź czy istniejąca sesja jest jeszcze ważna
            needs_login = True
            if LOGIN_STATE.exists():
                try:
                    ctx2 = browser.new_context(storage_state=str(LOGIN_STATE))
                    p2 = ctx2.new_page()
                    p2.goto(LIST_URL, wait_until="domcontentloaded", timeout=30_000)
                    if not _is_on_login_page(p2):
                        needs_login = False
                        ctx2.storage_state(path=str(LOGIN_STATE))
                        print(f"Sesja nadal ważna, odświeżono: {LOGIN_STATE}")
                    p2.close()
                    ctx2.close()
                except Exception:
                    pass

            if needs_login:
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)
                if auto:
                    print("Loguję automatycznie...")
                    _auto_login(page, login, haslo)
                else:
                    print("Zaloguj się do MyPrint w otwartym oknie przeglądarki.")
                    input("Po zalogowaniu i otwarciu listy faktur naciśnij ENTER...")

                page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60_000)

                if _is_on_login_page(page):
                    raise RuntimeError(
                        "Logowanie nie powiodło się — sprawdź login i hasło w pliku .env."
                    )

                export_link = page.locator(EXPORT_SELECTOR).first
                if export_link.count() == 0 or not export_link.is_visible():
                    raise RuntimeError(
                        "Lista faktur lub przycisk XLS nie są dostępne po zalogowaniu."
                    )

                context.storage_state(path=str(LOGIN_STATE))
                print(f"Sesja zapisana: {LOGIN_STATE}")
        finally:
            browser.close()


def main() -> int:
    try:
        save_session(headless=True)
        return 0
    except Exception as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
