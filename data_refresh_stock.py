import json
import os
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
STATUS_PATH = DATABASE_DIR / "stock_refresh_status.json"
LOCK_PATH = DATABASE_DIR / ".stock_refresh.lock"
DAILY_REFRESH_HOUR = 10
CHECK_INTERVAL_SECONDS = 15 * 60

_process_lock = threading.Lock()
_SESSION_EXPIRED_PHRASES = ("sesja myprint wygasła", "session expired", "save_login")


def _now() -> datetime:
    return datetime.now().astimezone()


def get_stock_refresh_status() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return {}
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_status(**values: Any) -> None:
    DATABASE_DIR.mkdir(exist_ok=True)
    status = get_stock_refresh_status()
    status.update(values)
    tmp = STATUS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATUS_PATH)


def _last_success() -> datetime | None:
    raw = get_stock_refresh_status().get("last_success")
    if raw:
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    db = DATABASE_DIR / "stock_dashboard.db"
    if db.exists():
        return datetime.fromtimestamp(db.stat().st_mtime).astimezone()
    return None


def refresh_is_due() -> bool:
    now = _now()
    today_target = now.replace(hour=DAILY_REFRESH_HOUR, minute=0, second=0, microsecond=0)
    if now < today_target:
        yesterday_target = today_target - timedelta(days=1)
        last = _last_success()
        return last is None or last < yesterday_target
    last = _last_success()
    return last is None or last < today_target


def _try_renew_session() -> None:
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "save_login.py")],
        cwd=BASE_DIR, capture_output=True, text=True, timeout=120, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Automatyczne odnowienie sesji nie powiodło się: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def _run_download(
    renew_on_expired: bool = True,
    analysis_date: date | None = None,
) -> tuple[Path, Path]:
    import subprocess, sys
    # Run Playwright in a separate process to avoid asyncio conflicts (e.g. Streamlit event loop)
    command = [sys.executable, str(BASE_DIR / "download_stock.py")]
    if analysis_date is not None:
        command.extend(["--date", analysis_date.isoformat()])
    result = subprocess.run(
        command,
        cwd=BASE_DIR, capture_output=True, text=True, timeout=300, check=False,
    )
    if result.returncode != 0:
        details = (result.stderr.strip() or result.stdout.strip()).lower()
        if renew_on_expired and any(p in details for p in _SESSION_EXPIRED_PHRASES):
            _try_renew_session()
            return _run_download(renew_on_expired=False, analysis_date=analysis_date)
        raise RuntimeError(
            result.stderr.strip() or result.stdout.strip()
            or "Proces pobierania stock zakończył się błędem."
        )
    downloads = BASE_DIR / "downloads"
    komp = sorted(downloads.glob("stock_komponenty_*.xlsx"), key=lambda p: p.stat().st_mtime)
    mag  = sorted(downloads.glob("stock_magazynowy_*.xlsx"),  key=lambda p: p.stat().st_mtime)
    if not komp or not mag:
        raise RuntimeError("Brak plików stock w downloads/ po pobraniu.")
    return komp[-1], mag[-1]


def run_refresh_stock(
    force: bool = False,
    analysis_date: date | None = None,
) -> dict[str, Any]:
    target_date = analysis_date or date.today()
    if analysis_date is None and not force and not refresh_is_due():
        return get_stock_refresh_status()
    if not _process_lock.acquire(blocking=False):
        return get_stock_refresh_status()

    lock_fd: int | None = None
    try:
        DATABASE_DIR.mkdir(exist_ok=True)
        try:
            lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return get_stock_refresh_status()

        _write_status(
            state="running",
            last_attempt=_now().isoformat(),
            requested_analysis_date=target_date.isoformat(),
            error=None,
        )
        path_komp, path_mag = _run_download(analysis_date=target_date)

        from import_stock import process_stock
        df = process_stock(analysis_date=target_date)

        _write_status(
            state="success",
            last_success=_now().isoformat(),
            analysis_date=target_date.isoformat(),
            source_komponenty=path_komp.name,
            source_magazynowy=path_mag.name,
            row_count=len(df),
            error=None,
            error_type=None,
        )
    except Exception as exc:
        msg = str(exc).strip() or f"{type(exc).__name__}: brak szczegółów"
        _write_status(state="error", error=msg, error_type=type(exc).__name__,
                      analysis_date=target_date.isoformat(),
                      last_attempt=_now().isoformat())
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
            LOCK_PATH.unlink(missing_ok=True)
        _process_lock.release()

    return get_stock_refresh_status()


def start_daily_refresh_stock() -> threading.Thread:
    def _worker() -> None:
        while True:
            run_refresh_stock()
            threading.Event().wait(CHECK_INTERVAL_SECONDS)

    thread = threading.Thread(target=_worker, name="stock-refresh", daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    import sys
    result = run_refresh_stock(force=True)
    state = result.get("state")
    if state == "success":
        print(f"OK: {result.get('row_count')} wierszy — {result.get('source_komponenty')}")
        sys.exit(0)
    else:
        print(f"BŁĄD: {result.get('error', 'nieznany')}", file=sys.stderr)
        sys.exit(1)
