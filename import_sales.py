from pathlib import Path
import re
import sqlite3
import pandas as pd

# ============================================================
# IMPORT SPRZEDAŻY Z MYPRINT DO SQLITE
# Źródło: downloads/myprint_faktury_sprzedazy_*.xls
# Główna miara sprzedaży: Wartość netto PLN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)

DB_PATH = DATABASE_DIR / "sales_dashboard.db"
TABLE_NAME = "sales_invoices"
ARCHIVE_PATH = BASE_DIR / "invoice_earchive.xlsx"


def find_latest_invoice_file() -> Path:
    files = []
    for pattern in ["*.xls", "*.xlsx", "*.csv"]:
        files.extend(DOWNLOADS_DIR.glob(pattern))

    if not files:
        raise FileNotFoundError(
            f"Brak plików XLS/XLSX/CSV w folderze: {DOWNLOADS_DIR}"
        )

    return max(files, key=lambda p: p.stat().st_mtime)


def normalize_column_name(name: str) -> str:
    name = str(name).strip().lower()

    replacements = {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
        "ó": "o", "ś": "s", "ż": "z", "ź": "z",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")

    return name


def read_myprint_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, sep=None, engine="python")
    else:
        # W pliku z MyPrint nagłówki są w 4. wierszu, czyli header=3
        df = pd.read_excel(path, header=3)

    df = df.dropna(how="all")
    df.columns = [normalize_column_name(c) for c in df.columns]

    return df


def clean_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "id_faktury": "invoice_id",
        "numer": "invoice_number",
        "kontrahent": "customer",
        "nip": "tax_id",
        "data_wystawienia": "invoice_date",
        "data_sprzedazy": "sales_date",
        "efaktura": "e_invoice",
        "typ": "invoice_type",
        "waluta": "currency",
        "wartosc_netto_pln": "sales_net_pln",
        "wartosc_netto_waluta": "sales_net_currency",
        "wartosc_vat_pln": "vat_pln",
        "wartosc_brutto_pln": "sales_gross_pln",
        "kraj": "country",
        "przydzielone_zaklady": "plant",
        "obce_id": "external_id",
        "wartosc_ruchow_mag_pln": "inventory_movements_pln",
        "numer_ksef": "ksef_number",
    }

    df = df.rename(columns=rename_map)

    # Usuwamy kolumny należnościowe / płatnicze, bo nie są używane w dashboardzie.
    columns_to_drop = [
        "zaplacono_pln",
        "zaplacono_waluta",
        "do_zaplaty",
        "termin",
        "termin_dni",
        "wartosc_vat_waluta",
        "wartosc_brutto_waluta",
    ]

    df = df.drop(columns=[c for c in columns_to_drop if c in df.columns], errors="ignore")

    required = ["invoice_id", "invoice_number", "customer", "invoice_date", "sales_net_pln"]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "Brakuje wymaganych kolumn po imporcie: "
            + ", ".join(missing)
            + "\nDostępne kolumny: "
            + ", ".join(df.columns)
        )

    # Konwersje dat
    for col in ["invoice_date", "sales_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Konwersje liczb
    numeric_cols = [
        "sales_net_pln",
        "sales_net_currency",
        "vat_pln",
        "sales_gross_pln",
        "inventory_movements_pln",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(" ", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Podstawowe czyszczenie tekstu
    text_cols = ["customer", "country", "currency", "invoice_type", "plant", "tax_id"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": "", "None": ""})

    # Główna miara sprzedaży
    df["sales_pln"] = df["sales_net_pln"]

    # Kolumny pomocnicze do dashboardu
    df["year"] = df["invoice_date"].dt.year
    df["month"] = df["invoice_date"].dt.month
    df["month_name"] = df["invoice_date"].dt.strftime("%Y-%m")
    df["quarter"] = "Q" + df["invoice_date"].dt.quarter.astype("Int64").astype(str)

    # Prosta klasyfikacja regionów
    def map_region(country):
        country = str(country).strip().upper()
        if country == "PL":
            return "Poland"
        if country in ["DE", "AT", "CH"]:
            return "DACH"
        if country in ["DK", "SE", "NO", "FI"]:
            return "Nordics"
        if country in ["FR", "BE", "NL", "LU"]:
            return "Western Europe"
        if country in ["CZ", "SK", "HU", "RO"]:
            return "CEE"
        if country == "":
            return "Unknown"
        return "Other"

    df["region"] = df["country"].apply(map_region)

    # Usuwamy puste wiersze bez faktury
    df = df[df["invoice_id"].notna()]
    df = df[df["invoice_number"].notna()]

    return df


def merge_with_archive(
    current_df: pd.DataFrame,
    archive_path: Path = ARCHIVE_PATH,
) -> pd.DataFrame:
    """Combine the current export with historical invoices and remove duplicates."""
    frames = []
    if archive_path.exists():
        archive_df = clean_sales_data(read_myprint_file(archive_path))
        frames.append(archive_df)

    # Keep current data last so it wins if an invoice also exists in the archive.
    frames.append(current_df)
    combined = pd.concat(frames, ignore_index=True, sort=False)

    invoice_ids = combined["invoice_id"].astype("string").str.strip()
    invoice_numbers = combined["invoice_number"].astype("string").str.strip()
    combined["_dedupe_key"] = invoice_ids.where(
        invoice_ids.notna() & invoice_ids.ne(""),
        "number:" + invoice_numbers,
    )
    combined = combined.drop_duplicates("_dedupe_key", keep="last")
    combined = combined.drop(columns="_dedupe_key")
    return combined.sort_values("invoice_date").reset_index(drop=True)


def save_to_sqlite(df: pd.DataFrame) -> None:
    conn = sqlite3.connect(DB_PATH)

    df.to_sql(
        TABLE_NAME,
        conn,
        if_exists="replace",
        index=False
    )

    conn.close()


def main():
    latest_file = find_latest_invoice_file()
    print(f"Importuję najnowszy plik: {latest_file}")

    raw_df = read_myprint_file(latest_file)
    clean_df = merge_with_archive(clean_sales_data(raw_df))

    save_to_sqlite(clean_df)

    print("")
    print("Import zakończony.")
    print(f"Baza danych: {DB_PATH}")
    print(f"Tabela: {TABLE_NAME}")
    print(f"Liczba faktur: {len(clean_df):,}")
    print(f"Sprzedaż netto PLN: {clean_df['sales_pln'].sum():,.2f}")

    print("")
    print("TOP 10 klientów:")
    top_customers = (
        clean_df.groupby("customer", dropna=False)["sales_pln"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )
    print(top_customers.to_string())


if __name__ == "__main__":
    main()
