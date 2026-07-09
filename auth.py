"""User authentication & authorization for Business Intelligence Hub.

- SQLite user store at database/users.db
- PBKDF2-SHA256 password hashing (stdlib only)
- Session tokens stored server-side; passed between pages via URL query param
  (this is how sessions survive `<a target="_blank">` navigation to new tabs)
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "users.db"

APPS = ("sales", "stock")
APP_LABELS = {"sales": "Sales", "stock": "Otiocon Stock"}

SESSION_TTL_DAYS = 7
PBKDF2_ITERATIONS = 200_000


# ── DB init ───────────────────────────────────────────────────────────────────

_schema_ready = False


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist yet. Cheap & idempotent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            must_change_password INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS permissions (
            username TEXT NOT NULL,
            app_name TEXT NOT NULL,
            PRIMARY KEY (username, app_name),
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
        """
    )
    conn.commit()


def _connect() -> sqlite3.Connection:
    global _schema_ready
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    if not _schema_ready:
        # Guards against pages/*.py being opened directly (e.g. via a
        # bookmarked ?token=... link), which in Streamlit's multipage
        # model runs ONLY that page's script, never app.py — so app.py's
        # init_db() call would otherwise never fire on a fresh container
        # and every auth query would hit "no such table: sessions".
        _ensure_schema(conn)
        _schema_ready = True
    return conn


def init_db() -> None:
    """Ensure tables exist and seed default admin if the users table is empty."""
    conn = _connect()
    try:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            conn.execute(
                "INSERT INTO users (username, password_hash, is_admin, must_change_password, created_at) VALUES (?, ?, 1, 1, ?)",
                ("admin", hash_password("admin"), datetime.now().isoformat()),
            )
            for app in APPS:
                conn.execute(
                    "INSERT INTO permissions (username, app_name) VALUES (?, ?)",
                    ("admin", app),
                )
            conn.commit()
    finally:
        conn.close()


# ── Password hashing ──────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    computed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return secrets.compare_digest(computed, expected)


# ── Sessions ──────────────────────────────────────────────────────────────────


def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(days=SESSION_TTL_DAYS)).isoformat()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO sessions (token, username, expires_at) VALUES (?, ?, ?)",
            (token, username, expires),
        )
        conn.commit()
    finally:
        conn.close()
    return token


def get_session_user(token: str) -> dict | None:
    """Return user dict if token is valid & not expired, else None."""
    if not token:
        return None
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT username, expires_at FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        if not row:
            return None
        username, expires_at = row
        if datetime.fromisoformat(expires_at) < datetime.now():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        user_row = conn.execute(
            "SELECT username, is_admin, must_change_password FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not user_row:
            return None
        perm_rows = conn.execute(
            "SELECT app_name FROM permissions WHERE username = ?", (username,)
        ).fetchall()
        return {
            "username": user_row[0],
            "is_admin": bool(user_row[1]),
            "must_change_password": bool(user_row[2]),
            "permissions": {r[0] for r in perm_rows},
        }
    finally:
        conn.close()


def delete_session(token: str) -> None:
    if not token:
        return
    conn = _connect()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


def purge_expired_sessions() -> None:
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM sessions WHERE expires_at < ?", (datetime.now().isoformat(),)
        )
        conn.commit()
    finally:
        conn.close()


# ── Auth ──────────────────────────────────────────────────────────────────────


def authenticate(username: str, password: str) -> dict | None:
    """Return user dict on success, None on failure."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT password_hash, is_admin, must_change_password FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            return None
        password_hash, is_admin, must_change = row
        if not verify_password(password, password_hash):
            return None
        perm_rows = conn.execute(
            "SELECT app_name FROM permissions WHERE username = ?", (username,)
        ).fetchall()
        return {
            "username": username,
            "is_admin": bool(is_admin),
            "must_change_password": bool(must_change),
            "permissions": {r[0] for r in perm_rows},
        }
    finally:
        conn.close()


# ── User management ───────────────────────────────────────────────────────────


def list_users() -> list[dict]:
    conn = _connect()
    try:
        user_rows = conn.execute(
            "SELECT username, is_admin, must_change_password, created_at FROM users ORDER BY username"
        ).fetchall()
        perm_rows = conn.execute("SELECT username, app_name FROM permissions").fetchall()
    finally:
        conn.close()
    perms_by_user: dict[str, set[str]] = {}
    for username, app_name in perm_rows:
        perms_by_user.setdefault(username, set()).add(app_name)
    return [
        {
            "username": u,
            "is_admin": bool(admin),
            "must_change_password": bool(must),
            "created_at": created,
            "permissions": perms_by_user.get(u, set()),
        }
        for u, admin, must, created in user_rows
    ]


def create_user(username: str, password: str, is_admin: bool = False) -> bool:
    """Return True on success, False if username already exists."""
    username = username.strip()
    if not username or not password:
        return False
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, is_admin, must_change_password, created_at) VALUES (?, ?, ?, 1, ?)",
            (username, hash_password(password), int(is_admin), datetime.now().isoformat()),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_user(username: str) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
    finally:
        conn.close()


def set_admin(username: str, is_admin: bool) -> None:
    conn = _connect()
    try:
        conn.execute(
            "UPDATE users SET is_admin = ? WHERE username = ?",
            (int(is_admin), username),
        )
        conn.commit()
    finally:
        conn.close()


def set_permission(username: str, app_name: str, granted: bool) -> None:
    if app_name not in APPS:
        raise ValueError(f"Unknown app: {app_name}")
    conn = _connect()
    try:
        if granted:
            conn.execute(
                "INSERT OR IGNORE INTO permissions (username, app_name) VALUES (?, ?)",
                (username, app_name),
            )
        else:
            conn.execute(
                "DELETE FROM permissions WHERE username = ? AND app_name = ?",
                (username, app_name),
            )
        conn.commit()
    finally:
        conn.close()


def change_password(username: str, new_password: str, clear_must_change: bool = True) -> None:
    conn = _connect()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = ? WHERE username = ?",
            (
                hash_password(new_password),
                0 if clear_must_change else 1,
                username,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def count_admins() -> int:
    conn = _connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0]
    finally:
        conn.close()
