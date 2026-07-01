import json
import os
import subprocess
import sys
import threading
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

from import_sales import (
    clean_sales_data,
    merge_with_archive,
    read_myprint_file,
    save_to_sqlite,
)


BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DB_PATH = DATABASE_DIR / "sales_dashboard.db"
STATUS_PATH = DATABASE_DIR / "refresh_status.json"
LOCK_PATH = DATABASE_DIR / ".refresh.lock"
DAILY_REFRESH_HOUR = 10  # pobieranie codziennie o 10:00
CHECK_INTERVAL_SECONDS = 15 * 60

_process_lock = threading.Lock()


_SESSION_EXPIRED_PHRASES = ("sesja myprint wygasła", "session expired", "save_login")


def _renew_session_isolated() -> None:
    """Re-login to MyPrint using credentials from .env (headless)."""
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "save_login.py")],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Automatyczne odnowienie sesji nie powiodło się: {details}"
        )


def _download_invoice_isolated(renew_on_expired: bool = True) -> Path:
    """Run Playwright outside Streamlit's event loop and return the new export."""
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "download_invoices.py")],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr.strip() or result.stdout.strip()).lower()
        if renew_on_expired and any(p in details for p in _SESSION_EXPIRED_PHRASES):
            _renew_session_isolated()
            return _download_invoice_isolated(renew_on_expired=False)
        raise RuntimeError(
            result.stderr.strip() or result.stdout.strip()
            or "Proces pobierania MyPrint zakończył się błędem."
        )

    invoice_files = [
        path
        for pattern in ("*.xls", "*.xlsx", "*.csv")
        for path in (BASE_DIR / "downloads").glob(pattern)
    ]
    if not invoice_files:
        raise RuntimeError("MyPrint nie utworzył pliku z fakturami.")
    return max(invoice_files, key=lambda path: path.stat().st_mtime)


def _now() -> datetime:
    return datetime.now().astimezone()


def get_refresh_status() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return {}
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_status(**values: Any) -> None:
    DATABASE_DIR.mkdir(exist_ok=True)
    status = get_refresh_status()
    status.update(values)
    temporary_path = STATUS_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary_path.replace(STATUS_PATH)


def _last_success() -> datetime | None:
    value = get_refresh_status().get("last_success")
    if value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    if DB_PATH.exists():
        return datetime.fromtimestamp(DB_PATH.stat().st_mtime).astimezone()
    return None


def refresh_is_due() -> bool:
    now = _now()
    today_target = now.replace(
        hour=DAILY_REFRESH_HOUR, minute=0, second=0, microsecond=0
    )
    if now < today_target:
        # Przed 10:00 — sprawdź czy odświeżono już po wczorajszym targecie
        yesterday_target = today_target - timedelta(days=1)
        last_success = _last_success()
        return last_success is None or last_success < yesterday_target
    # Po 10:00 — sprawdź czy już odświeżono dzisiaj po 10:00
    last_success = _last_success()
    return last_success is None or last_success < today_target


def run_refresh(force: bool = False) -> dict[str, Any]:
    """Download, transform, and store MyPrint data if the daily refresh is due."""
    if not force and not refresh_is_due():
        return get_refresh_status()

    if not _process_lock.acquire(blocking=False):
        return get_refresh_status()

    lock_descriptor: int | None = None
    try:
        DATABASE_DIR.mkdir(exist_ok=True)
        try:
            lock_descriptor = os.open(
                LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY
            )
        except FileExistsError:
            return get_refresh_status()

        started_at = _now().isoformat()
        _write_status(state="running", last_attempt=started_at, error=None)
        invoice_file = _download_invoice_isolated()
        current_data = clean_sales_data(read_myprint_file(invoice_file))
        dataframe = merge_with_archive(current_data)
        save_to_sqlite(dataframe)
        _write_status(
            state="success",
            last_success=_now().isoformat(),
            source_file=invoice_file.name,
            row_count=len(dataframe),
            error=None,
        )
    except Exception as exc:
        message = str(exc).strip()
        if not message:
            message = f"{type(exc).__name__}: brak szczegółowego komunikatu"
        _write_status(
            state="error",
            error=message,
            error_type=type(exc).__name__,
            last_attempt=_now().isoformat(),
        )
    finally:
        if lock_descriptor is not None:
            os.close(lock_descriptor)
            LOCK_PATH.unlink(missing_ok=True)
        _process_lock.release()

    return get_refresh_status()


def start_daily_refresh() -> threading.Thread:
    """Start one daemon that checks every 15 minutes for a due daily refresh."""
    def worker() -> None:
        while True:
            run_refresh()
            threading.Event().wait(CHECK_INTERVAL_SECONDS)

    thread = threading.Thread(target=worker, name="myprint-refresh", daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    import sys
    result = run_refresh(force=True)
    state = result.get("state")
    if state == "success":
        print(f"OK: pobrano {result.get('row_count')} faktur z {result.get('source_file')}")
        sys.exit(0)
    else:
        print(f"BŁĄD: {result.get('error', 'nieznany błąd')}", file=sys.stderr)
        sys.exit(1)
