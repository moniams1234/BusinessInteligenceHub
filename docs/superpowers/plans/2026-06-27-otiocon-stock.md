# Otiocon Stock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the "W przygotowaniu" placeholder on Otiocon Stock with a full inventory aging & reserve dashboard powered by daily Playwright downloads from MyPrint.

**Architecture:** `download_stock.py` (Playwright) pulls two filtered XLS exports from MyPrint (Komponenty + Magazynowy/Stock) into `downloads/`. `import_stock.py` merges them, applies PROWAX/RW/WIP/FG mapping, computes aging buckets and reserve amounts, stores in `database/stock_dashboard.db`. `data_refresh_stock.py` runs this daily at 10:00 in a background thread. `pages/Otiocon_Stock.py` reads the DB and renders KPIs, four charts, and filterable data tables.

**Tech Stack:** Python 3.12, Streamlit, Playwright (sync), pandas, plotly.express, openpyxl, SQLite3

## Global Constraints

- Python 3, four-space indentation, UTF-8 files, PEP 8
- `snake_case` for functions/variables, `UPPER_SNAKE_CASE` for constants
- `pathlib.Path` for all filesystem paths
- Dark CSS theme identical to `pages/Sales.py` (radial gradient background)
- `myprint_login.json` must exist before download works (created by `save_login.py`)
- Stock xlsx files: sheet name `"MyPrint"`, `header=3` → 21 columns, data starts at `iloc[0]`
- SQLite table: `stock_data` in `database/stock_dashboard.db`
- All monetary values in PLN; `stock_value` column is the primary financial measure
- Spec: `docs/superpowers/specs/2026-06-27-otiocon-stock-design.md`

---

### Task 1: Fetch default_mapping.xlsx from inventory_app2

**Files:**
- Create: `data/default_mapping.xlsx`

**Interfaces:**
- Produces: `data/default_mapping.xlsx` with sheets `Mapp1` (cols: Index materiałowy, Rodzaj indeksu) and `Mapp2` (cols: Magazyn, Typ surowca, Type of materials)

- [ ] **Step 1: Create `data/` directory and download the mapping file**

```bash
mkdir -p "C:/Users/48519/Documents/Monika/Szkolenia inne/Vibecoding/Project/data"
```

Then in Python (run from project root):

```python
import urllib.request
url = "https://raw.githubusercontent.com/moniams1234/inventory_app2/main/data/default_mapping.xlsx"
urllib.request.urlretrieve(url, "data/default_mapping.xlsx")
print("Downloaded.")
```

- [ ] **Step 2: Verify sheet structure**

```python
import pandas as pd
xl = pd.ExcelFile("data/default_mapping.xlsx")
print("Sheets:", xl.sheet_names)           # expect: ['Mapp1', 'Mapp2']
m1 = pd.read_excel(xl, sheet_name="Mapp1")
m2 = pd.read_excel(xl, sheet_name="Mapp2")
print("Mapp1 cols:", list(m1.columns))
print("Mapp2 cols:", list(m2.columns))
print(m1.head(3))
print(m2.head(3))
```

Expected: Mapp1 has at least 2 columns (material index → PROWAX/NON PROWAX). Mapp2 has at least 3 columns (Magazyn, Typ surowca, Type of materials → RW/WIP/FG).

- [ ] **Step 3: Commit**

```bash
git add data/default_mapping.xlsx
git commit -m "feat: add default PROWAX/RW/WIP/FG mapping file from inventory_app2"
```

---

### Task 2: import_stock.py — data processing pipeline

**Files:**
- Create: `import_stock.py`
- Create: `tests/test_import_stock.py`

**Interfaces:**
- Consumes: `data/default_mapping.xlsx`; two xlsx files from `downloads/` named `stock_komponenty_*.xlsx` and `stock_magazynowy_*.xlsx`
- Produces:
  - `load_mapping(path: Path) → tuple[pd.DataFrame, pd.DataFrame]`
  - `read_stock_file(path: Path) → pd.DataFrame` — standardized column names, no repeated header row
  - `merge_stock_files(df1: pd.DataFrame, df2: pd.DataFrame) → pd.DataFrame`
  - `apply_mapping(df: pd.DataFrame, mapp1: pd.DataFrame, mapp2: pd.DataFrame) → pd.DataFrame` — adds `rodzaj_indeksu`, `type_of_materials`
  - `calculate_aging(df: pd.DataFrame, analysis_date: date) → pd.DataFrame` — adds `aging_bucket`
  - `calculate_reserves(df: pd.DataFrame) → pd.DataFrame` — adds `reserve_pct`, `reserve_amount`
  - `assign_status(df: pd.DataFrame) → pd.DataFrame` — adds `status`
  - `find_latest_stock_files() → tuple[Path | None, Path | None]`
  - `save_to_sqlite(df: pd.DataFrame) → None`
  - `process_stock(analysis_date: date | None, mapping_path: Path) → pd.DataFrame`

- [ ] **Step 1: Create tests directory and write failing tests**

```bash
mkdir -p tests
```

Create `tests/test_import_stock.py`:

```python
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _stock_row(**overrides):
    row = {
        "material_index": "895-26-452-09",
        "warehouse": "Glasshouse",
        "material_type": "Komponenty",
        "receipt_date": pd.Timestamp("2024-01-15"),
        "stock_value": 100.0,
        "material_name": "10 NOWAX, OEM",
        "rodzaj_indeksu": None,
        "type_of_materials": None,
        "aging_bucket": None,
    }
    row.update(overrides)
    return pd.DataFrame([row])


BASE = Path(__file__).parent.parent


class TestReadStockFile:
    def test_returns_standard_columns(self):
        from import_stock import read_stock_file
        path = BASE / "material_stat_daystock (63).xlsx"
        if not path.exists():
            pytest.skip("Sample file not present")
        df = read_stock_file(path)
        for col in ("material_index", "warehouse", "material_type", "receipt_date", "stock_value"):
            assert col in df.columns, f"Missing column: {col}"

    def test_no_repeated_header_row(self):
        from import_stock import read_stock_file
        path = BASE / "material_stat_daystock (63).xlsx"
        if not path.exists():
            pytest.skip("Sample file not present")
        df = read_stock_file(path)
        assert df.iloc[0]["material_index"] != "Index materiałowy"

    def test_row_count_komponenty(self):
        from import_stock import read_stock_file
        path = BASE / "material_stat_daystock (63).xlsx"
        if not path.exists():
            pytest.skip("Sample file not present")
        df = read_stock_file(path)
        assert len(df) == 506

    def test_row_count_magazynowy(self):
        from import_stock import read_stock_file
        path = BASE / "material_stat_daystock (64).xlsx"
        if not path.exists():
            pytest.skip("Sample file not present")
        df = read_stock_file(path)
        assert len(df) == 1921

    def test_stock_value_is_numeric(self):
        from import_stock import read_stock_file
        path = BASE / "material_stat_daystock (63).xlsx"
        if not path.exists():
            pytest.skip("Sample file not present")
        df = read_stock_file(path)
        assert pd.api.types.is_numeric_dtype(df["stock_value"])


class TestMergeStockFiles:
    def test_concat_two_frames(self):
        from import_stock import merge_stock_files
        df1 = _stock_row(material_type="Komponenty")
        df2 = _stock_row(material_type="Magazynowy / Stock")
        merged = merge_stock_files(df1, df2)
        assert len(merged) == 2
        assert set(merged["material_type"]) == {"Komponenty", "Magazynowy / Stock"}

    def test_index_reset(self):
        from import_stock import merge_stock_files
        merged = merge_stock_files(_stock_row(), _stock_row())
        assert list(merged.index) == [0, 1]


class TestCalculateAging:
    @pytest.mark.parametrize("receipt,bucket", [
        ("2026-05-01", "0-3 mcy"),
        ("2026-01-01", "3-6 mcy"),
        ("2025-10-01", "6-9 mcy"),
        ("2025-07-01", "9-12 mcy"),
        ("2024-01-01", "pow 12 mcy"),
    ])
    def test_bucket_assignment(self, receipt, bucket):
        from import_stock import calculate_aging
        df = _stock_row(receipt_date=pd.Timestamp(receipt))
        result = calculate_aging(df, date(2026, 6, 27))
        assert result.iloc[0]["aging_bucket"] == bucket

    def test_invalid_date_gets_blad_daty(self):
        from import_stock import calculate_aging
        df = _stock_row(receipt_date=pd.NaT)
        result = calculate_aging(df, date(2026, 6, 27))
        assert result.iloc[0]["aging_bucket"] == "błąd daty"


class TestCalculateReserves:
    @pytest.mark.parametrize("mat_type,bucket,expected_pct", [
        ("RW",      "0-3 mcy",    0.0),
        ("RW",      "9-12 mcy",   0.5),
        ("RW",      "pow 12 mcy", 1.0),
        ("WIP",     "3-6 mcy",    0.5),
        ("WIP",     "6-9 mcy",    1.0),
        ("FG",      "3-6 mcy",    0.0),
        ("FG",      "6-9 mcy",    1.0),
        ("UNMAPPED","pow 12 mcy", 0.0),
    ])
    def test_reserve_pct(self, mat_type, bucket, expected_pct):
        from import_stock import calculate_reserves
        df = _stock_row(type_of_materials=mat_type, stock_value=200.0)
        df["aging_bucket"] = bucket
        result = calculate_reserves(df)
        assert result.iloc[0]["reserve_pct"] == expected_pct

    def test_reserve_amount_is_value_times_pct(self):
        from import_stock import calculate_reserves
        df = _stock_row(type_of_materials="RW", stock_value=200.0)
        df["aging_bucket"] = "pow 12 mcy"
        result = calculate_reserves(df)
        assert result.iloc[0]["reserve_amount"] == pytest.approx(200.0)

    def test_blad_daty_gets_zero(self):
        from import_stock import calculate_reserves
        df = _stock_row(type_of_materials="WIP", stock_value=100.0)
        df["aging_bucket"] = "błąd daty"
        result = calculate_reserves(df)
        assert result.iloc[0]["reserve_pct"] == 0.0
        assert result.iloc[0]["reserve_amount"] == 0.0
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd "C:/Users/48519/Documents/Monika/Szkolenia inne/Vibecoding/Project"
python -m pytest tests/test_import_stock.py -v 2>&1 | head -20
```

Expected: `ImportError: No module named 'import_stock'`

- [ ] **Step 3: Implement import_stock.py**

Create `import_stock.py`:

```python
import sqlite3
from datetime import date
from pathlib import Path

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
    ("RW",  "0-3 mcy"):    0.0,
    ("RW",  "3-6 mcy"):    0.0,
    ("RW",  "6-9 mcy"):    0.0,
    ("RW",  "9-12 mcy"):   0.5,
    ("RW",  "pow 12 mcy"): 1.0,
    ("WIP", "0-3 mcy"):    0.0,
    ("WIP", "3-6 mcy"):    0.5,
    ("WIP", "6-9 mcy"):    1.0,
    ("WIP", "9-12 mcy"):   1.0,
    ("WIP", "pow 12 mcy"): 1.0,
    ("FG",  "0-3 mcy"):    0.0,
    ("FG",  "3-6 mcy"):    0.0,
    ("FG",  "6-9 mcy"):    1.0,
    ("FG",  "9-12 mcy"):   1.0,
    ("FG",  "pow 12 mcy"): 1.0,
}


def load_mapping(path: Path = MAPPING_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    xl = pd.ExcelFile(path)
    return pd.read_excel(xl, sheet_name="Mapp1"), pd.read_excel(xl, sheet_name="Mapp2")


def read_stock_file(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="MyPrint", header=3)
    df = df.dropna(how="all").reset_index(drop=True)
    if len(df.columns) == len(STOCK_COLUMNS):
        df.columns = STOCK_COLUMNS
    else:
        # Fallback for files where row 2 (not 3) is empty — use header=2 + skip repeated row
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
    # Mapp1 col A = material index, col B = PROWAX/NON PROWAX
    m1_cols = list(mapp1.columns)
    prowax_set = set(
        mapp1[m1_cols[0]].dropna().astype(str).str.strip().str.upper()
    )
    df["rodzaj_indeksu"] = df["material_index"].apply(
        lambda x: "PROWAX" if str(x).strip().upper() in prowax_set else "NON PROWAX"
    )
    # Mapp2 col A = Magazyn, col B = Typ surowca, col C = RW/WIP/FG
    m2_cols = list(mapp2.columns)
    lookup = {
        (str(r[m2_cols[0]]).strip(), str(r[m2_cols[1]]).strip()): str(r[m2_cols[2]]).strip()
        for _, r in mapp2.iterrows()
        if pd.notna(r[m2_cols[0]]) and pd.notna(r[m2_cols[1]])
    }
    df["type_of_materials"] = df.apply(
        lambda r: lookup.get(
            (str(r.get("warehouse", "")).strip(), str(r.get("material_type", "")).strip()),
            "UNMAPPED",
        ),
        axis=1,
    )
    return df


def calculate_aging(df: pd.DataFrame, analysis_date: date) -> pd.DataFrame:
    df = df.copy()
    ref = pd.Timestamp(analysis_date)

    def _bucket(dt: pd.Timestamp) -> str:
        if pd.isna(dt):
            return "błąd daty"
        months = (ref.year - dt.year) * 12 + (ref.month - dt.month)
        if months < 3:
            return "0-3 mcy"
        if months < 6:
            return "3-6 mcy"
        if months < 9:
            return "6-9 mcy"
        if months < 12:
            return "9-12 mcy"
        return "pow 12 mcy"

    df["aging_bucket"] = df["receipt_date"].apply(_bucket)
    return df


def calculate_reserves(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    def _pct(row: pd.Series) -> float:
        bucket = row.get("aging_bucket", "błąd daty")
        mat = row.get("type_of_materials", "UNMAPPED")
        if bucket == "błąd daty":
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
    df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
    conn.close()


def process_stock(
    analysis_date: date | None = None,
    mapping_path: Path = MAPPING_PATH,
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
            print(f"Uwaga: {unmapped} pozycji UNMAPPED — sprawdź mapping.")
    except Exception as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_import_stock.py -v
```

Expected: all 20 tests PASS.

- [ ] **Step 5: Smoke test with sample files**

The sample files (`material_stat_daystock (63).xlsx`, `(64).xlsx`) need to be in `downloads/` with correct names for `process_stock()`. Run a direct merge test instead:

```python
from pathlib import Path
from import_stock import read_stock_file, merge_stock_files, load_mapping, apply_mapping, calculate_aging, calculate_reserves
from datetime import date

df63 = read_stock_file(Path("material_stat_daystock (63).xlsx"))
df64 = read_stock_file(Path("material_stat_daystock (64).xlsx"))
df = merge_stock_files(df63, df64)
print(f"Merged rows: {len(df)}")  # expect 2427

mapp1, mapp2 = load_mapping()
df = apply_mapping(df, mapp1, mapp2)
df = calculate_aging(df, date.today())
df = calculate_reserves(df)
print(f"Wartość: {df['stock_value'].sum():,.2f} PLN")
print(f"Rezerwy: {df['reserve_amount'].sum():,.2f} PLN")
print(f"UNMAPPED: {(df['type_of_materials']=='UNMAPPED').sum()}")
```

Expected: `Merged rows: 2427`, no errors.

- [ ] **Step 6: Commit**

```bash
git add import_stock.py tests/test_import_stock.py
git commit -m "feat: import_stock — merge Komponenty+Stock, aging, rezerwy, SQLite"
```

---

### Task 3: download_stock.py — Playwright download of two stock exports

**Files:**
- Create: `download_stock.py`

**Interfaces:**
- Consumes: `myprint_login.json`
- Produces:
  - `download_stock(headless: bool) → tuple[Path, Path]` — `(path_komponenty, path_magazynowy)`
  - Files saved as `downloads/stock_komponenty_{timestamp}.xlsx` and `downloads/stock_magazynowy_{timestamp}.xlsx`

Note: Playwright requires a live authenticated MyPrint session — no automated unit tests possible. Verification is manual (Step 2).

- [ ] **Step 1: Implement download_stock.py**

Create `download_stock.py`:

```python
import argparse
import sys
from datetime import datetime
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


def _click_filter(page) -> None:
    btn = page.locator(_FILTER_BTN_SELECTOR).first
    btn.wait_for(state="visible", timeout=10_000)
    btn.click()
    page.wait_for_load_state("domcontentloaded", timeout=30_000)


def _download_one_type(page, type_label: str, output_path: Path) -> Path:
    page.goto(STOCK_URL, wait_until="domcontentloaded", timeout=60_000)
    _check_session(page)
    _select_type_filter(page, type_label)
    _click_filter(page)
    export_btn = page.locator(_EXPORT_SELECTOR).first
    export_btn.wait_for(state="visible", timeout=15_000)
    with page.expect_download(timeout=60_000) as dl_info:
        export_btn.click(timeout=15_000)
    dl_info.value.save_as(str(output_path))
    return output_path


def download_stock(headless: bool = True) -> tuple[Path, Path]:
    if not LOGIN_STATE.exists():
        raise FileNotFoundError(
            "Brak pliku myprint_login.json. Najpierw uruchom save_login.py."
        )
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path_komp = DOWNLOAD_DIR / f"stock_komponenty_{ts}.xlsx"
    path_mag = DOWNLOAD_DIR / f"stock_magazynowy_{ts}.xlsx"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            try:
                ctx = browser.new_context(
                    storage_state=str(LOGIN_STATE),
                    accept_downloads=True,
                )
                page = ctx.new_page()
                _download_one_type(page, "Komponenty", path_komp)
                _download_one_type(page, "Magazynowy / Stock", path_mag)
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
    args = parser.parse_args()
    try:
        path_komp, path_mag = download_stock(headless=not args.headed)
    except Exception as exc:
        print(f"Błąd pobierania: {exc}", file=sys.stderr)
        return 1
    print(f"Pobrano Komponenty:  {path_komp}")
    print(f"Pobrano Magazynowy:  {path_mag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Test manually with --headed**

```bash
python download_stock.py --headed
```

Watch the browser:
1. Opens MyPrint stock page
2. Sets filter to "Komponenty" → clicks filtruj → clicks export → file downloads
3. Sets filter to "Magazynowy / Stock" → clicks filtruj → clicks export → file downloads

Expected output:
```
Pobrano Komponenty:  downloads/stock_komponenty_2026-06-27_HH-MM-SS.xlsx
Pobrano Magazynowy:  downloads/stock_magazynowy_2026-06-27_HH-MM-SS.xlsx
```

If selectors don't match: open DevTools on the MyPrint page, inspect the "Typ surowca" dropdown and the filtruj/export buttons, update `_select_type_filter` and `_EXPORT_SELECTOR` / `_FILTER_BTN_SELECTOR` accordingly.

- [ ] **Step 3: Verify downloaded files parse correctly**

```python
from pathlib import Path
from import_stock import read_stock_file

komp = sorted(Path("downloads").glob("stock_komponenty_*.xlsx"))[-1]
mag  = sorted(Path("downloads").glob("stock_magazynowy_*.xlsx"))[-1]
df1 = read_stock_file(komp)
df2 = read_stock_file(mag)
print("Komponenty rows:", len(df1), "| types:", df1["material_type"].unique())
print("Magazynowy rows:", len(df2), "| types:", df2["material_type"].unique())
```

Expected: df1 has only `"Komponenty"`, df2 has only `"Magazynowy / Stock"`.

- [ ] **Step 4: Run full process_stock() with downloaded files**

```bash
python import_stock.py
```

Expected:
```
Import zakończony. Wiersze: ~2427
Wartość magazynowa: XXXXX PLN
Rezerwy: XXXXX PLN
```

- [ ] **Step 5: Commit**

```bash
git add download_stock.py
git commit -m "feat: download_stock — Playwright pobiera Komponenty i Magazynowy/Stock z MyPrint"
```

---

### Task 4: data_refresh_stock.py — daily background refresh thread

**Files:**
- Create: `data_refresh_stock.py`

**Interfaces:**
- Consumes: `download_stock.download_stock()`, `import_stock.process_stock()`
- Produces:
  - `get_stock_refresh_status() → dict[str, Any]`
  - `run_refresh_stock(force: bool = False) → dict[str, Any]`
  - `start_daily_refresh_stock() → threading.Thread`

- [ ] **Step 1: Implement data_refresh_stock.py**

Create `data_refresh_stock.py`:

```python
import json
import os
import threading
from datetime import datetime, timedelta
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


def _run_download(renew_on_expired: bool = True) -> tuple[Path, Path]:
    from download_stock import download_stock
    try:
        return download_stock(headless=True)
    except RuntimeError as exc:
        details = str(exc).lower()
        if renew_on_expired and any(p in details for p in _SESSION_EXPIRED_PHRASES):
            _try_renew_session()
            return _run_download(renew_on_expired=False)
        raise


def run_refresh_stock(force: bool = False) -> dict[str, Any]:
    if not force and not refresh_is_due():
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

        _write_status(state="running", last_attempt=_now().isoformat(), error=None)
        path_komp, path_mag = _run_download()

        from import_stock import process_stock
        from datetime import date
        df = process_stock(analysis_date=date.today())

        _write_status(
            state="success",
            last_success=_now().isoformat(),
            source_komponenty=path_komp.name,
            source_magazynowy=path_mag.name,
            row_count=len(df),
            error=None,
        )
    except Exception as exc:
        msg = str(exc).strip() or f"{type(exc).__name__}: brak szczegółów"
        _write_status(state="error", error=msg, error_type=type(exc).__name__,
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
```

- [ ] **Step 2: Verify refresh logic with existing DB (no live download needed)**

```python
from data_refresh_stock import get_stock_refresh_status, refresh_is_due
print("Status:", get_stock_refresh_status())
print("Refresh due:", refresh_is_due())
```

- [ ] **Step 3: Commit**

```bash
git add data_refresh_stock.py
git commit -m "feat: data_refresh_stock — daily background refresh dla stock pipeline"
```

---

### Task 5: pages/Otiocon_Stock.py — full dashboard

**Files:**
- Modify: `pages/Otiocon_Stock.py` (full replacement)

**Interfaces:**
- Consumes:
  - `data_refresh_stock.get_stock_refresh_status`, `run_refresh_stock`, `start_daily_refresh_stock`
  - `import_stock.apply_mapping`, `calculate_aging`, `calculate_reserves`, `load_mapping`
  - SQLite `database/stock_dashboard.db` table `stock_data`
  - `data/default_mapping.xlsx`
- Produces: Streamlit page at `/Otiocon_Stock`

- [ ] **Step 1: Replace placeholder with full dashboard**

Overwrite `pages/Otiocon_Stock.py` with:

```python
import io
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from data_refresh_stock import (
    get_stock_refresh_status,
    run_refresh_stock,
    start_daily_refresh_stock,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "stock_dashboard.db"
MAPPING_PATH = BASE_DIR / "data" / "default_mapping.xlsx"
TABLE_NAME = "stock_data"

BUCKET_ORDER = ["0-3 mcy", "3-6 mcy", "6-9 mcy", "9-12 mcy", "pow 12 mcy", "błąd daty"]
PALETTE = ["#22C55E", "#2563EB", "#F59E0B", "#EF4444", "#8B5CF6", "#6B7280"]

st.set_page_config(
    page_title="Otiocon Stock",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    [data-testid="stSidebarNav"]     { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    header[data-testid="stHeader"]   { display: none; }
    footer                           { display: none; }
    .stApp {
        background: radial-gradient(ellipse at 20% 20%, #1a2f5a 0%, #0F172A 55%, #091120 100%);
        min-height: 100vh;
    }
    .block-container { padding: 1.5rem 2rem !important; max-width: 100% !important; }
    .kpi-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        margin-bottom: 8px;
    }
    .kpi-label { font-size: 0.75rem; color: #8FB0E6; letter-spacing: 0.08em;
                 text-transform: uppercase; margin-bottom: 6px; }
    .kpi-value { font-size: 1.75rem; font-weight: 800; color: #EAF1FF; }
    .kpi-sub   { font-size: 0.78rem; color: #5580B5; margin-top: 4px; }
    .stButton > button {
        background: rgba(255,255,255,0.07) !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        border-radius: 10px !important;
        color: #8FB0E6 !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Background refresh (once per session) ──────────────────────────────────
if "stock_refresh_started" not in st.session_state:
    start_daily_refresh_stock()
    st.session_state["stock_refresh_started"] = True

# ── Status bar ─────────────────────────────────────────────────────────────
status = get_stock_refresh_status()
state = status.get("state", "")
hdr_l, hdr_r = st.columns([7, 1])
with hdr_l:
    if state == "success":
        last = status.get("last_success", "")[:16].replace("T", " ")
        st.success(f"✓ Dane aktualne · {last} · {status.get('row_count','—')} pozycji")
    elif state == "running":
        st.info("⟳ Trwa pobieranie danych z MyPrint…")
    elif state == "error":
        st.error(f"✗ Błąd synchronizacji: {status.get('error','')}")
    else:
        st.warning("Brak danych — kliknij Odśwież lub uruchom download_stock.py")
with hdr_r:
    if st.button("↻ Odśwież dane"):
        with st.spinner("Synchronizacja z MyPrint…"):
            run_refresh_stock(force=True)
        st.rerun()

# ── Title ──────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="color:#EAF1FF;font-size:1.8rem;font-weight:800;margin:8px 0 2px;">'
    '📦 Otiocon Stock</h1>'
    '<p style="color:#8FB0E6;font-size:0.88rem;margin:0 0 16px;">'
    'Wiekowanie zapasów i kalkulacja rezerw</p>',
    unsafe_allow_html=True,
)

# ── Mapping panel ──────────────────────────────────────────────────────────
with st.expander("⚙️ Mapping — PROWAX / RW / WIP / FG", expanded=False):
    mapping_source = st.radio("Źródło mappingu:", ["Domyślny", "Wgraj własny"], horizontal=True)
    uploaded_mapping = None

    if mapping_source == "Domyślny":
        if MAPPING_PATH.exists():
            mapp1_preview, mapp2_preview = pd.read_excel(MAPPING_PATH, sheet_name="Mapp1"), \
                                           pd.read_excel(MAPPING_PATH, sheet_name="Mapp2")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.caption("Mapp1 — PROWAX / NON PROWAX")
                st.dataframe(mapp1_preview, use_container_width=True, height=180)
            with col_m2:
                st.caption("Mapp2 — Typ materiału (RW / WIP / FG)")
                st.dataframe(mapp2_preview, use_container_width=True, height=180)
            with open(MAPPING_PATH, "rb") as fh:
                st.download_button(
                    "↓ Pobierz default_mapping.xlsx",
                    data=fh.read(),
                    file_name="default_mapping.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        else:
            st.warning("Brak pliku data/default_mapping.xlsx — uruchom Task 1 z planu.")
        active_mapping_path: Path | None = MAPPING_PATH
    else:
        uploaded_mapping = st.file_uploader(
            "Wgraj mapping.xlsx (wymagane arkusze: Mapp1, Mapp2)",
            type=["xlsx"],
        )
        active_mapping_path = uploaded_mapping  # type: ignore[assignment]

# ── Analysis date ──────────────────────────────────────────────────────────
analysis_date = st.date_input("📅 Data analizy", value=date.today())

# ── Load data ──────────────────────────────────────────────────────────────
if not DB_PATH.exists():
    st.error(
        "Brak bazy danych stock. Kliknij **↻ Odśwież dane** powyżej, "
        "lub uruchom `python download_stock.py` a następnie `python import_stock.py`."
    )
    if st.button("← Wróć do menu"):
        st.switch_page("app.py")
    st.stop()

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
conn.close()

if df.empty:
    st.warning("Baza danych jest pusta.")
    st.stop()

df["receipt_date"] = pd.to_datetime(df["receipt_date"], errors="coerce")
df["stock_value"]  = pd.to_numeric(df["stock_value"], errors="coerce").fillna(0.0)

# Re-apply mapping/aging when custom mapping or different analysis date
stored_date = df["analysis_date"].iloc[0] if "analysis_date" in df.columns else ""
needs_recalc = (
    mapping_source == "Wgraj własny" and uploaded_mapping is not None
) or (str(analysis_date) != stored_date)

if needs_recalc and active_mapping_path is not None:
    from import_stock import apply_mapping, calculate_aging, calculate_reserves, load_mapping
    m1, m2 = load_mapping(active_mapping_path)
    df = apply_mapping(df, m1, m2)
    df = calculate_aging(df, analysis_date)
    df = calculate_reserves(df)
else:
    df["reserve_pct"]    = pd.to_numeric(df.get("reserve_pct", 0),    errors="coerce").fillna(0.0)
    df["reserve_amount"] = pd.to_numeric(df.get("reserve_amount", 0), errors="coerce").fillna(0.0)

# ── KPI cards ──────────────────────────────────────────────────────────────
total_value   = df["stock_value"].sum()
total_reserve = df["reserve_amount"].sum()
pct_reserve   = (total_reserve / total_value * 100) if total_value > 0 else 0.0
n_items       = len(df)

k1, k2, k3, k4 = st.columns(4)
for col, label, val, sub in [
    (k1, "Wartość magazynowa",  f"{total_value:,.0f} PLN",   ""),
    (k2, "Kwota rezerwy",       f"{total_reserve:,.0f} PLN", ""),
    (k3, "% rezerwy",           f"{pct_reserve:.1f}%",       "rezerwa / wartość"),
    (k4, "Liczba pozycji",      f"{n_items:,}",              "wierszy w bazie"),
]:
    col.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{val}</div>'
        f'<div class="kpi-sub">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

_chart_bg = {"paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)",
             "font_color": "#EAF1FF", "title_font_color": "#EAF1FF",
             "legend_font_color": "#8FB0E6"}

# ── Row 1 charts ───────────────────────────────────────────────────────────
col_c1, col_c2 = st.columns(2)

with col_c1:
    if "rodzaj_indeksu" in df.columns:
        pie_df = df.groupby("rodzaj_indeksu")["stock_value"].sum().reset_index()
        fig = px.pie(pie_df, names="rodzaj_indeksu", values="stock_value",
                     color_discrete_sequence=["#2563EB", "#0EA5A4"],
                     title="PROWAX vs NON PROWAX (wartość mag.)")
        fig.update_layout(**_chart_bg)
        st.plotly_chart(fig, use_container_width=True)

with col_c2:
    if "type_of_materials" in df.columns and "aging_bucket" in df.columns:
        aging_df = (df.groupby(["type_of_materials", "aging_bucket"])["stock_value"]
                    .sum().reset_index())
        fig = px.bar(aging_df, x="type_of_materials", y="stock_value", color="aging_bucket",
                     category_orders={"aging_bucket": BUCKET_ORDER},
                     color_discrete_sequence=PALETTE, barmode="stack",
                     title="Struktura wiekowa per typ materiału",
                     labels={"stock_value": "Wartość mag. (PLN)", "type_of_materials": "Typ"})
        fig.update_layout(**_chart_bg)
        st.plotly_chart(fig, use_container_width=True)

# ── Row 2 charts ───────────────────────────────────────────────────────────
col_c3, col_c4 = st.columns(2)

with col_c3:
    if "warehouse" in df.columns:
        wh_df = (df.groupby("warehouse")[["stock_value", "reserve_amount"]].sum()
                 .nlargest(10, "reserve_amount").reset_index()
                 .melt(id_vars="warehouse",
                       value_vars=["stock_value", "reserve_amount"],
                       var_name="Typ", value_name="Wartość PLN"))
        wh_df["Typ"] = wh_df["Typ"].map({"stock_value": "Wartość mag.", "reserve_amount": "Rezerwa"})
        fig = px.bar(wh_df, x="Wartość PLN", y="warehouse", color="Typ",
                     orientation="h", barmode="group",
                     color_discrete_map={"Wartość mag.": "#2563EB", "Rezerwa": "#EF4444"},
                     title="Top 10 magazynów — wartość vs rezerwa")
        fig.update_layout(**_chart_bg)
        st.plotly_chart(fig, use_container_width=True)

with col_c4:
    if "type_of_materials" in df.columns:
        res_df = df.groupby("type_of_materials")["reserve_amount"].sum().reset_index()
        fig = px.bar(res_df, x="type_of_materials", y="reserve_amount",
                     color="type_of_materials", color_discrete_sequence=PALETTE,
                     title="Rezerwy per typ materiału (RW / WIP / FG)",
                     labels={"reserve_amount": "Rezerwa (PLN)", "type_of_materials": "Typ"})
        fig.update_layout(**_chart_bg, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# ── Data tabs ──────────────────────────────────────────────────────────────
tab_det, tab_sum = st.tabs(["📋 Szczegóły", "📊 Podsumowanie"])

DETAIL_COLS = [c for c in [
    "material_index", "material_name", "warehouse", "material_type",
    "type_of_materials", "rodzaj_indeksu", "receipt_date",
    "aging_bucket", "stock_value", "reserve_pct", "reserve_amount", "status",
] if c in df.columns]

with tab_det:
    fc1, fc2, fc3, fc4 = st.columns(4)
    all_wh   = ["— wszystkie —"] + sorted(df["warehouse"].dropna().unique().tolist())
    all_type = ["— wszystkie —"] + sorted(df.get("type_of_materials", pd.Series()).dropna().unique().tolist())
    all_rodz = ["— wszystkie —"] + sorted(df.get("rodzaj_indeksu",    pd.Series()).dropna().unique().tolist())
    all_buck = ["— wszystkie —"] + [b for b in BUCKET_ORDER if b in df.get("aging_bucket", pd.Series()).values]

    sel_wh   = fc1.selectbox("Magazyn",        all_wh,   key="det_wh")
    sel_type = fc2.selectbox("Typ materiału",  all_type, key="det_type")
    sel_rodz = fc3.selectbox("Rodzaj indeksu", all_rodz, key="det_rodz")
    sel_buck = fc4.selectbox("Wiek",           all_buck, key="det_buck")

    flt = df.copy()
    if sel_wh   != "— wszystkie —": flt = flt[flt["warehouse"]          == sel_wh]
    if sel_type != "— wszystkie —": flt = flt[flt["type_of_materials"]  == sel_type]
    if sel_rodz != "— wszystkie —": flt = flt[flt["rodzaj_indeksu"]     == sel_rodz]
    if sel_buck != "— wszystkie —": flt = flt[flt["aging_bucket"]       == sel_buck]

    st.caption(f"{len(flt):,} pozycji po filtracji")
    st.dataframe(flt[DETAIL_COLS], use_container_width=True, height=400)

with tab_sum:
    group_cols = [c for c in ["warehouse", "type_of_materials", "rodzaj_indeksu", "status"]
                  if c in df.columns]
    summary = (df.groupby(group_cols)[["stock_value", "reserve_amount"]]
               .sum().round(2).reset_index())
    totals = pd.DataFrame([{
        **{c: ("SUMA" if i == 0 else "") for i, c in enumerate(group_cols)},
        "stock_value": summary["stock_value"].sum(),
        "reserve_amount": summary["reserve_amount"].sum(),
    }])
    summary = pd.concat([summary, totals], ignore_index=True)
    st.dataframe(summary, use_container_width=True, height=400)

# ── Export ─────────────────────────────────────────────────────────────────
def _build_excel(detail: pd.DataFrame, summ: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        detail.to_excel(w, sheet_name="Szczegoly", index=False)
        summ.to_excel(w, sheet_name="Podsumowanie", index=False)
    return buf.getvalue()


exp_col, back_col = st.columns([5, 1])
with exp_col:
    excel_bytes = _build_excel(flt[DETAIL_COLS], summary)
    st.download_button(
        "↓ Eksport Excel",
        data=excel_bytes,
        file_name=f"otiocon_stock_{analysis_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
with back_col:
    if st.button("← Wróć do menu"):
        st.switch_page("app.py")
```

- [ ] **Step 2: Verify in browser**

Open http://localhost:8501 (restart Streamlit if needed), click **Otiocon Stock** tile. Check:

1. Status bar shows correct state (success/error/warning)
2. Mapping expander: Mapp1 + Mapp2 tables visible, download button works
3. "Wgraj własny" radio: file uploader appears
4. Date picker defaults to today
5. KPI cards show 4 values (not 0/blank)
6. 4 charts render without errors (pie, stacked bar, horizontal bar, grouped bar)
7. Szczegóły tab: filters work, table shows correct columns
8. Podsumowanie tab: pivot table with SUMA row
9. Export button downloads valid xlsx with 2 sheets
10. "← Wróć do menu" navigates back to hub

- [ ] **Step 3: Commit**

```bash
git add pages/Otiocon_Stock.py
git commit -m "feat: Otiocon Stock — dashboard wiekowania zapasów, rezerwy, mapping, eksport"
```

---

## Self-Review

**Spec coverage:**
- ✅ `download_stock.py` — Playwright, 2 filtry (Komponenty + Magazynowy/Stock), login check, błędy sesji
- ✅ `import_stock.py` — merge, STOCK_COLUMNS, Mapp1/Mapp2, aging 5 buckets, tabela rezerw, SQLite
- ✅ `data_refresh_stock.py` — background thread, 10:00 daily, lock, session renewal
- ✅ `data/default_mapping.xlsx` — pobrany z inventory_app2
- ✅ Status bar + przycisk Odśwież — Task 5
- ✅ Mapping panel: podgląd Mapp1/Mapp2, download, upload własnego — Task 5
- ✅ Date picker z recalc — Task 5
- ✅ 4 KPI cards — Task 5
- ✅ 4 wykresy (pie PROWAX, stacked aging, top-10 wh, rezerwy per typ) — Task 5
- ✅ Zakładki Szczegóły (4 filtry) + Podsumowanie (pivot + SUMA) — Task 5
- ✅ Eksport Excel (2 arkusze) — Task 5
- ✅ Przycisk "← Wróć do menu" — Task 5
- ✅ Obsługa błędów: brak login.json, brak DB, UNMAPPED, błąd daty — Task 3, 4, 5

**Placeholder scan:** Brak TBD / TODO.

**Type consistency:**
- `read_stock_file(path: Path) → pd.DataFrame` — Task 2 implementuje, Task 3 Step 3 konsumuje ✅
- `process_stock(analysis_date, mapping_path) → pd.DataFrame` — Task 2 implementuje, Task 4 konsumuje ✅
- `get_stock_refresh_status() → dict` — Task 4 implementuje, Task 5 importuje ✅
- `run_refresh_stock(force=False) → dict` — Task 4 implementuje, Task 5 wywołuje ✅
- `start_daily_refresh_stock() → Thread` — Task 4 implementuje, Task 5 wywołuje ✅
- `load_mapping(path) → (mapp1, mapp2)` — Task 2 implementuje, Task 5 używa przy recalc ✅
