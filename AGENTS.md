# Repository Guidelines

## Project Structure & Module Organization

The repository implements a small MyPrint sales-data pipeline:

- `save_login.py` creates the local Playwright session file.
- `download_invoices.py` downloads invoice exports into `downloads/`.
- `import_sales.py` merges the newest export with `invoice_earchive.xlsx`, deduplicates invoices, and replaces the `sales_invoices` table in `database/sales_dashboard.db`.
- `app.py` is the Streamlit dashboard entry point.
- `test_playwright.py` is an interactive Playwright smoke check, not an automated test suite.
- `app/` is currently empty and reserved for future modularization.

Treat files in `downloads/`, `database/`, and `myprint_login.json` as generated or local runtime data, not source code.

## Build, Test, and Development Commands

Create and activate a virtual environment, then install the runtime packages explicitly:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install streamlit pandas plotly playwright openpyxl xlrd
playwright install chromium
```

Run the workflow from the repository root:

```powershell
python save_login.py          # interactively save a MyPrint login session
python download_invoices.py   # download the latest invoice export
python import_sales.py        # rebuild the local SQLite table
streamlit run app.py          # launch the dashboard
python test_playwright.py     # manually verify browser automation
```

## Coding Style & Naming Conventions

Use Python 3, four-space indentation, UTF-8 files, and PEP 8 conventions. Name functions and variables with `snake_case`, constants with `UPPER_SNAKE_CASE`, and modules with short lowercase names. Use `pathlib.Path` for filesystem paths and keep data transformations in small, testable functions. Preserve source column mappings in `clean_sales_data()` when extending imports.

## Testing Guidelines

No automated framework or coverage threshold is configured. For data changes, add `pytest` tests under `tests/`, named `test_<module>.py`; focus on column normalization, required-column validation, numeric parsing, and region mapping. Before submitting, run the full download/import/dashboard path with non-production sample data.

## Commit & Pull Request Guidelines

Git history is unavailable in this working copy. Use concise imperative commits such as `Add invoice currency filter`. Keep each commit scoped to one change. Pull requests should explain the user-visible effect, list verification commands, identify schema or generated-data impacts, and include screenshots for dashboard changes.

## Security & Configuration

Never commit `myprint_login.json`, invoice exports, or production SQLite databases; they may contain credentials or customer data. Avoid logging invoice contents and use sanitized fixtures in tests and reviews.
