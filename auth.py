"""User authentication & authorization for Business Intelligence Hub.

- Postgres (Supabase) user store — persists across Streamlit Cloud
  container restarts/redeploys, unlike the old SQLite-based store whose
  file lived on an ephemeral filesystem and was wiped on every redeploy.
- PBKDF2-SHA256 password hashing (stdlib only)
- Session tokens stored server-side; passed between pages via URL query param
  (this is how sessions survive `<a target="_blank">` navigation to new tabs)

Connection string is read from Streamlit secrets (SUPABASE_DB_URL), with an
environment-variable fallback for local/non-Streamlit scripts.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta

import psycopg2
import streamlit as st

APPS = ("sales", "stock")
APP_LABELS = {"sales": "Sales", "stock": "Otiocon Stock"}

SESSION_TTL_DAYS = 7
PBKDF2_ITERATIONS = 200_000


# ── DB connection ─────────────────────────────────────────────────────────────

_schema_ready = False


def _get_dsn() -> str:
    try:
        dsn = st.secrets["SUPABASE_DB_URL"]
        if dsn:
            return dsn
    except Exception:
        pass
    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError(
            "Brak SUPABASE_DB_URL. Dodaj go w Streamlit Cloud -> Settings -> "
            "Secrets (albo w .streamlit/secrets.toml lokalnie)."
        )
    return dsn


def _ensure_schema(cur) -> None:
    """Create tables if they don't exist yet. Cheap & idempotent."""
    cur.execute(
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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS permissions (
            username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
            app_name TEXT NOT NULL,
            PRIMARY KEY (username, app_name)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
            expires_at TEXT NOT NULL
        )
        """
    )


def _connect():
    global _schema_ready
    conn = psycopg2.connect(_get_dsn(), sslmode="require")
    if not _schema_ready:
        # Guards against pages/*.py being opened directly (e.g. via a
        # bookmarked ?token=... link), which in Streamlit's multipage
        # model runs ONLY that page's script, never app.py.
        with conn.cursor() as cur:
            _ensure_schema(cur)
        conn.commit()
        _schema_ready = True
    return conn


def init_db() -> None:
    """Ensure tables exist and seed default admin if the users table is empty."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
            if count == 0:
                cur.execute(
                    "INSERT INTO users (username, password_hash, is_admin, must_change_password, created_at) "
                    "VALUES (%s, %s, 1, 1, %s)",
                    ("admin", hash_password("admin"), datetime.now().isoformat()),
                )
                for app in APPS:
                    cur.execute(
                        "INSERT INTO permissions (username, app_name) VALUES (%s, %s)",
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
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (token, username, expires_at) VALUES (%s, %s, %s)",
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
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, expires_at FROM sessions WHERE token = %s", (token,)
            )
            row = cur.fetchone()
            if not row:
                return None
            username, expires_at = row
            if datetime.fromisoformat(expires_at) < datetime.now():
                cur.execute("DELETE FROM sessions WHERE token = %s", (token,))
                conn.commit()
                return None
            cur.execute(
                "SELECT username, is_admin, must_change_password FROM users WHERE username = %s",
                (username,),
            )
            user_row = cur.fetchone()
            if not user_row:
                return None
            cur.execute(
                "SELECT app_name FROM permissions WHERE username = %s", (username,)
            )
            perm_rows = cur.fetchall()
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
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE token = %s", (token,))
        conn.commit()
    finally:
        conn.close()


def purge_expired_sessions() -> None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM sessions WHERE expires_at < %s", (datetime.now().isoformat(),)
            )
        conn.commit()
    finally:
        conn.close()


# ── Auth ──────────────────────────────────────────────────────────────────────


def authenticate(username: str, password: str) -> dict | None:
    """Return user dict on success, None on failure."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT password_hash, is_admin, must_change_password FROM users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
            if not row:
                return None
            password_hash, is_admin, must_change = row
            if not verify_password(password, password_hash):
                return None
            cur.execute(
                "SELECT app_name FROM permissions WHERE username = %s", (username,)
            )
            perm_rows = cur.fetchall()
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
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, is_admin, must_change_password, created_at FROM users ORDER BY username"
            )
            user_rows = cur.fetchall()
            cur.execute("SELECT username, app_name FROM permissions")
            perm_rows = cur.fetchall()
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
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO users (username, password_hash, is_admin, must_change_password, created_at) "
                    "VALUES (%s, %s, %s, 1, %s)",
                    (username, hash_password(password), int(is_admin), datetime.now().isoformat()),
                )
            except psycopg2.IntegrityError:
                conn.rollback()
                return False
        conn.commit()
        return True
    finally:
        conn.close()


def delete_user(username: str) -> None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
    finally:
        conn.close()


def set_admin(username: str, is_admin: bool) -> None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_admin = %s WHERE username = %s",
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
        with conn.cursor() as cur:
            if granted:
                cur.execute(
                    "INSERT INTO permissions (username, app_name) VALUES (%s, %s) "
                    "ON CONFLICT (username, app_name) DO NOTHING",
                    (username, app_name),
                )
            else:
                cur.execute(
                    "DELETE FROM permissions WHERE username = %s AND app_name = %s",
                    (username, app_name),
                )
        conn.commit()
    finally:
        conn.close()


def change_password(username: str, new_password: str, clear_must_change: bool = True) -> None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s, must_change_password = %s WHERE username = %s",
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
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
            return cur.fetchone()[0]
    finally:
        conn.close()
