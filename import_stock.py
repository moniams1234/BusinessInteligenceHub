import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DATABASE_DIR = BASE_DIR / "database"
DB_PATH = DATABASE_DIR / "stock_dashboard.db"
MAPPING_PATH = BASE_DIR / "data" / "default_mapping.xlsx"
TABLE_NAME = "stock_data"

STOCK_COLUMNS = [
    "material_index", "batch", "barcode", "supplier_code", "warehouse",
    "pz_number", "invoice1", "invoice2", "material_name", "material_type",
    "stock_qty", "unit1", "stock_qty2", "unit2", "stock_qty3", "unit3",
    "stock_value", "currency", "receipt_date", "dkk_rate", "stock_value_dkk",
]

RESERVE_TABLE: dict[tuple[str, str], float] = {
    ("RW", "0-3 mcy"): 0.0,
    ("RW", "3-6 mcy"): 0.0,
    ("RW", "6-9 mcy"): 0.0,
    ("RW", "9-12 mcy"): 0.5,
    ("RW", "pow 12 mcy"): 1.0,
    ("WIP", "0-3 mcy"): 0.0,
    ("WIP", "3-6 mcy"): 0.5,
    ("WIP", "6-9 mcy"): 1.0,
    ("WIP", "9-12 mcy"): 1.0,
    ("WIP", "pow 12 mcy"): 1.0,
    ("FG", "0-3 mcy"): 0.0,
    ("FG", "3-6 mcy"): 0.0,
    ("FG", "6-9 mcy"): 1.0,
    ("FG", "9-12 mcy"): 1.0,
    ("FG", "pow 12 mcy"): 1.0,
}


def _read_mapp1(file_obj: Any) -> pd.DataFrame:
    """Read PROWAX indexes from column B of Mapp1, as in inventory_app2."""
    raw = pd.read_excel(file_obj, sheet_name="Mapp1", header=None)
    if raw.shape[1] < 2:
        raise ValueError("Mapp1 must contain PROWAX indexes in column B.")

    indexes = raw.iloc[:, 1].dropna().astype(str).str.strip()
    indexes = indexes[indexes.ne("") & indexes.ne("Row Labels")]
    return pd.DataFrame({"prowax_index": indexes})


def _read_mapp2(file_obj: Any) -> pd.DataFrame:
    """Find the Mapp2 header row dynamically and keep the mapping columns."""
    raw = pd.read_excel(file_obj, sheet_name="Mapp2", header=None)
    expected = {"Type of materials", "Magazyn", "Typ surowca"}

    header_row = None
    for idx, row in raw.iterrows():
        values = {str(value).strip() for value in row if pd.notna(value)}
        if expected.issubset(values):
            header_row = idx
            break

    if header_row is None:
        raise ValueError(
            "Mapp2 must contain headers: Type of materials, Magazyn, Typ surowca."
        )

    mapping = raw.iloc[header_row:].copy()
    mapping.columns = [
        str(value).strip() if pd.notna(value) else f"_col{idx}"
        for idx, value in enumerate(mapping.iloc[0])
    ]
    mapping = mapping.iloc[1:].reset_index(drop=True)
    mapping = mapping[["Type of materials", "Magazyn", "Typ surowca"]].copy()
    mapping = mapping.dropna(subset=["Magazyn", "Typ surowca"])
    mapping = mapping.apply(lambda column: column.astype(str).str.strip())
    return mapping


def load_mapping(path: Any = MAPPING_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _read_mapp1(path), _read_mapp2(path)


def read_stock_file(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="MyPrint", header=3)
    df = df.dropna(how="all").reset_index(drop=True)
    if len(df.columns) == len(STOCK_COLUMNS):
        df.columns = STOCK_COLUMNS
    else:
        df = pd.read_excel(path, sheet_name="MyPrint", header=2)
        df = df.iloc[1:].reset_index(drop=True).dropna(how="all").reset_index(drop=True)
        if len(df.columns) == len(STOCK_COLUMNS):
            df.columns = STOCK_COLUMNS
    df["stock_value"] = pd.to_numeric(df["stock_value"], errors="coerce").fillna(0.0)
    df["receipt_date"] = pd.to_datetime(df["receipt_date"], errors="coerce")
    return df


def merge_stock_files(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([df1, df2], ignore_index=True)


def apply_mapping(
    df: pd.DataFrame,
    mapp1: pd.DataFrame,
    mapp2: pd.DataFrame,
) -> pd.DataFrame:
    df = df.copy()

    if "prowax_index" not in mapp1.columns:
        source_column = 1 if mapp1.shape[1] > 1 else 0
        mapp1 = pd.DataFrame({"prowax_index": mapp1.iloc[:, source_column]})
    prowax_set = set(
        mapp1["prowax_index"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
        .loc[lambda values: values.ne("") & values.ne("row labels")]
    )
    normalized_index = df["material_index"].astype(str).str.strip().str.lower()
    df["rodzaj_indeksu"] = normalized_index.apply(
        lambda value: "PROWAX" if value in prowax_set else "NON PROWAX"
    )

    required = {"Type of materials", "Magazyn", "Typ surowca"}
    missing = required.difference(mapp2.columns)
    if missing:
        raise ValueError("Missing Mapp2 columns: " + ", ".join(sorted(missing)))

    mapp2 = mapp2.copy()
    mapp2 = mapp2.apply(lambda column: column.astype(str).str.strip())
    mapp2["Type of materials"] = mapp2["Type of materials"].replace(
        {"x": "UNMAPPED", "X": "UNMAPPED", "": "UNMAPPED"}
    )
    lookup = {
        (row["Magazyn"], row["Typ surowca"]): row["Type of materials"]
        for _, row in mapp2.iterrows()
        if row["Magazyn"] and row["Typ surowca"]
    }

    df["type_of_materials"] = df.apply(
        lambda row: lookup.get(
            (
                str(row.get("warehouse", "")).strip(),
                str(row.get("material_type", "")).strip(),
            ),
            "UNMAPPED",
        ),
        axis=1,
    )
    return df


def calculate_aging(df: pd.DataFrame, analysis_date: date) -> pd.DataFrame:
    df = df.copy()
    ref = pd.Timestamp(analysis_date)
    receipt_dates = pd.to_datetime(df["receipt_date"], errors="coerce")

    def _bucket(dt: pd.Timestamp) -> str:
        if pd.isna(dt):
            return "błąd daty"
        if dt > ref:
            return "data > dzień analizy"
        months = (ref.year - dt.year) * 12 + (ref.month - dt.month)
        if ref.day < dt.day:
            months -= 1
        if months < 3:
            return "0-3 mcy"
        if months < 6:
            return "3-6 mcy"
        if months < 9:
            return "6-9 mcy"
        if months < 12:
            return "9-12 mcy"
        return "pow 12 mcy"

    df["receipt_date"] = receipt_dates
    df["aging_bucket"] = receipt_dates.apply(_bucket)
    return df


def calculate_reserves(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    def _pct(row: pd.Series) -> float:
        bucket = row.get("aging_bucket", "błąd daty")
        mat = row.get("type_of_materials", "UNMAPPED")
        if bucket in {"błąd daty", "data > dzień analizy"}:
            return 0.0
        if mat in {"UNMAPPED", "x", "X"}:
            return 0.0
        return RESERVE_TABLE.get((mat, bucket), 0.0)

    df["reserve_pct"] = df.apply(_pct, axis=1)
    df["reserve_amount"] = df["stock_value"] * df["reserve_pct"]
    return df


def assign_status(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    prowax_cutoff = pd.Timestamp("2023-11-01")
    nonprowax_cutoff = pd.Timestamp("2023-12-01")

    def _status(row: pd.Series) -> str:
        dt = row.get("receipt_date")
        if pd.isna(dt):
            return "do weryfikacji"
        cutoff = prowax_cutoff if row.get("rodzaj_indeksu") == "PROWAX" else nonprowax_cutoff
        return "nowa" if dt >= cutoff else "nabyta"

    df["status"] = df.apply(_status, axis=1)
    return df


def find_latest_stock_files() -> tuple[Path | None, Path | None]:
    komp = sorted(DOWNLOADS_DIR.glob("stock_komponenty_*.xlsx"), key=lambda p: p.stat().st_mtime)
    mag = sorted(DOWNLOADS_DIR.glob("stock_magazynowy_*.xlsx"), key=lambda p: p.stat().st_mtime)
    return (komp[-1] if komp else None, mag[-1] if mag else None)


def save_to_sqlite(df: pd.DataFrame) -> None:
    DATABASE_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        analysis_date = None
        if "analysis_date" in df.columns and not df.empty:
            analysis_date = str(df["analysis_date"].iloc[0])

        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (TABLE_NAME,),
        ).fetchone()

        if not table_exists:
            df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
        elif analysis_date:
            columns = [row[1] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})")]
            if "analysis_date" not in columns:
                conn.execute(f"DROP TABLE {TABLE_NAME}")
                df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
            else:
                conn.execute(
                    f"DELETE FROM {TABLE_NAME} WHERE analysis_date = ?",
                    (analysis_date,),
                )
                df.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
        else:
            df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
        conn.commit()
    finally:
        conn.close()


def process_stock(
    analysis_date: date | None = None,
    mapping_path: Any = MAPPING_PATH,
) -> pd.DataFrame:
    if analysis_date is None:
        analysis_date = date.today()
    mapp1, mapp2 = load_mapping(mapping_path)
    path_komp, path_mag = find_latest_stock_files()
    if path_komp is None or path_mag is None:
        raise FileNotFoundError(
            "Brak plików stock w downloads/. Uruchom download_stock.py."
        )
    df = merge_stock_files(read_stock_file(path_komp), read_stock_file(path_mag))
    df = apply_mapping(df, mapp1, mapp2)
    df = calculate_aging(df, analysis_date)
    df = calculate_reserves(df)
    df = assign_status(df)
    df["analysis_date"] = analysis_date.isoformat()
    save_to_sqlite(df)
    return df


if __name__ == "__main__":
    import sys
    try:
        df = process_stock()
        print(f"Import zakończony. Wiersze: {len(df)}")
        print(f"Wartość magazynowa: {df['stock_value'].sum():,.2f} PLN")
        print(f"Rezerwy: {df['reserve_amount'].sum():,.2f} PLN")
        unmapped = (df["type_of_materials"] == "UNMAPPED").sum()
        if unmapped:
            print(f"Uwaga: {unmapped} pozycji UNMAPPED - sprawdź mapping.")
    except Exception as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        sys.exit(1)
