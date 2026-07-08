"""
Wysyła codzienne powiadomienie na Discord ze sprzedażą dzień do dnia per klient.
Uruchamiany przez Windows Task Scheduler codziennie o 10:30.

Konfiguracja: ustaw zmienną środowiskową DISCORD_WEBHOOK_URL
lub podmień wartość WEBHOOK_URL poniżej.
"""

import json
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "sales_dashboard.db"

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


def _query_day(conn: sqlite3.Connection, day: date) -> dict[str, float]:
    """Zwraca {klient: suma_sprzedaży_netto_PLN} dla podanego dnia."""
    day_str = day.strftime("%Y-%m-%d")
    rows = conn.execute(
        """
        SELECT customer, SUM(sales_pln)
        FROM sales_invoices
        WHERE DATE(invoice_date) = ?
        GROUP BY customer
        """,
        (day_str,),
    ).fetchall()
    return {row[0]: row[1] for row in rows if row[0]}


def _find_last_two_days(conn: sqlite3.Connection) -> tuple[date, date]:
    """Zwraca dwie ostatnie daty z bazy (dzisiaj lub ostatnia dostępna + poprzednia)."""
    rows = conn.execute(
        "SELECT DISTINCT DATE(invoice_date) FROM sales_invoices ORDER BY invoice_date DESC LIMIT 2"
    ).fetchall()
    if len(rows) < 2:
        raise RuntimeError("Za mało dni w bazie danych (minimum 2).")
    today_d = date.fromisoformat(rows[0][0])
    prev_d = date.fromisoformat(rows[1][0])
    return today_d, prev_d


def build_message(today: date, prev: date, today_sales: dict, prev_sales: dict) -> dict:
    """Buduje payload Discord embed."""
    total_today = sum(today_sales.values())
    total_prev = sum(prev_sales.values())
    total_diff = total_today - total_prev
    total_pct = (total_diff / total_prev * 100) if total_prev else 0.0

    total_arrow = "📈" if total_diff >= 0 else "📉"
    sign = "+" if total_diff >= 0 else ""

    # Wiersze per klient — posortowane wg wzrostu PLN malejąco
    all_customers = sorted(
        set(today_sales) | set(prev_sales),
        key=lambda c: today_sales.get(c, 0) - prev_sales.get(c, 0),
        reverse=True,
    )

    lines = []
    for customer in all_customers:
        t = today_sales.get(customer, 0.0)
        p = prev_sales.get(customer, 0.0)
        diff = t - p
        pct = (diff / p * 100) if p else 0.0
        arrow = "▲" if diff >= 0 else "▼"
        diff_sign = "+" if diff >= 0 else ""
        lines.append(
            f"{arrow} **{customer}**\n"
            f"  dziś: `{t:,.0f} PLN` | zmiana: `{diff_sign}{diff:,.0f} PLN` ({diff_sign}{pct:.1f}%)"
        )

    # Discord embed ma limit 4096 znaków w opisie — przytnij jeśli za dużo klientów
    description = "\n".join(lines)
    if len(description) > 3800:
        description = description[:3800] + "\n…*(lista skrócona)*"

    color = 0x22C55E if total_diff >= 0 else 0xEF4444  # zielony / czerwony

    return {
        "embeds": [
            {
                "title": f"{total_arrow} Sprzedaż dzienna MyPrint — {today.strftime('%d.%m.%Y')}",
                "description": description,
                "color": color,
                "fields": [
                    {
                        "name": "Łącznie dziś",
                        "value": f"`{total_today:,.0f} PLN`",
                        "inline": True,
                    },
                    {
                        "name": f"vs {prev.strftime('%d.%m.%Y')}",
                        "value": f"`{sign}{total_diff:,.0f} PLN` ({sign}{total_pct:.1f}%)",
                        "inline": True,
                    },
                ],
                "footer": {"text": "MyPrint · Sales Dashboard · dane z bazy lokalnej"},
            }
        ]
    }


def send_to_discord(payload: dict, webhook_url: str) -> None:
    resp = requests.post(
        webhook_url,
        json=payload,
        headers={"User-Agent": "MyPrintBot/1.0"},
        timeout=15,
    )
    if resp.status_code not in (200, 204):
        raise RuntimeError(f"Discord zwrócił status {resp.status_code}: {resp.text}")


def main() -> None:
    if not WEBHOOK_URL:
        raise SystemExit(
            "Brak DISCORD_WEBHOOK_URL. "
            "Ustaw zmienną środowiskową lub wpisz URL bezpośrednio w discord_notify.py"
        )

    if not DB_PATH.exists():
        raise SystemExit(f"Brak bazy danych: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        today, prev = _find_last_two_days(conn)
        today_sales = _query_day(conn, today)
        prev_sales = _query_day(conn, prev)

    if not today_sales:
        raise SystemExit(f"Brak faktur dla {today} w bazie — pomijam powiadomienie.")

    payload = build_message(today, prev, today_sales, prev_sales)
    send_to_discord(payload, WEBHOOK_URL)
    print(f"OK: powiadomienie wysłane dla {today} ({len(today_sales)} klientów)")


if __name__ == "__main__":
    main()
