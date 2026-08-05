"""
Pings the Supabase Postgres database with a trivial query.

Supabase's free tier auto-pauses a project after 7 days with no API
activity. This script exists purely to be run on a schedule (see
.github/workflows/supabase-keepalive.yml) so the project never goes
7 full days without a connection, and the app never surprises users
with "psycopg2.OperationalError" from a sleeping database.

Requires the SUPABASE_DB_URL secret to be set as a GitHub Actions
repository secret (Settings -> Secrets and variables -> Actions).
This is the SAME connection string used in Streamlit Cloud's secrets,
just duplicated into GitHub's secret store since Actions runs
independently of Streamlit Cloud.
"""

import os
import sys

import psycopg2


def main() -> int:
    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        print("Brak SUPABASE_DB_URL w środowisku (sekret GitHub Actions).", file=sys.stderr)
        return 1

    try:
        conn = psycopg2.connect(dsn, sslmode="require", connect_timeout=15)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            print("OK: Supabase odpowiedziało, projekt pozostaje aktywny.")
            return 0
        finally:
            conn.close()
    except Exception as exc:
        print(f"Błąd podczas pingowania Supabase: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
