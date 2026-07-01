# Otiocon Stock — Design Spec
_Data: 2026-06-27_

## Cel

Zbudowanie w pełni działającej strony **Otiocon Stock** (zastępuje placeholder "W przygotowaniu") jako modułu istniejącej aplikacji Streamlit. Strona pokazuje wiekowanie zapasów i kalkulację rezerw na podstawie danych pobieranych codziennie z MyPrint przez Playwright — analogicznie do istniejącego pipeline'u sprzedaży.

---

## Źródło danych

Dwie osobne strony eksportu w MyPrint pod tym samym URL:
`https://myprint.graphicwest.biz/system/material_stat_daystockPart.php?action=menu`

Eksport 1 — filtr **Typ surowca = Komponenty** → plik xlsx (~506 wierszy)
Eksport 2 — filtr **Typ surowca = Magazynowy / Stock** → plik xlsx (~1921 wierszy)

Oba pliki trafiają do `downloads/` z timestampem w nazwie. Połączone dają ~2427 wierszy (identycznie jak `połaczony.xlsx`).

Kolumny wejściowe (header w row 2, index=2 przy pd.read_excel):
`Index materiałowy, Partia, Kod kreskowy, Kod dostawcy, Magazyn, Przyjęcie [PZ], Numer faktury (x2), Nazwa materiału, Typ surowca, Stan mag., jm.1, Stan mag. jm.2, Stan mag. jm.3, Wartość mag., waluta, Data przyjęcia, Kurs DKK, Wartość DKK`

---

## Nowe pliki

```
Project/
├── download_stock.py              # Playwright — pobiera 2 eksporty z MyPrint
├── import_stock.py                # Merge + clean → SQLite stock_dashboard.db
├── data_refresh_stock.py          # Background thread (wzorzec data_refresh.py)
├── data/
│   └── default_mapping.xlsx       # Mapp1 + Mapp2 (skopiowany z inventory_app2)
├── database/
│   ├── stock_dashboard.db         # tabela: stock_data
│   └── stock_refresh_status.json  # stan synchronizacji
└── pages/
    └── Otiocon_Stock.py           # zastępuje placeholder
```

---

## `download_stock.py`

Wzorzec identyczny z `download_invoices.py`:
- Używa `myprint_login.json` (Playwright storage state)
- Sprawdza czy sesja nie wygasła
- **Krok 1:** Przejdź na URL → ustaw filtr "Typ surowca" = "Komponenty" → kliknij "filtruj" → kliknij przycisk eksportu → pobierz plik do `downloads/stock_komponenty_{timestamp}.xlsx`
- **Krok 2:** Ustaw filtr "Typ surowca" = "Magazynowy / Stock" → kliknij "filtruj" → kliknij eksport → pobierz do `downloads/stock_magazynowy_{timestamp}.xlsx`
- Zwraca tuple `(path_komponenty, path_magazynowy)`
- Obsługa błędów: wygasła sesja, timeout, brak przycisku eksportu

---

## `import_stock.py`

```
find_latest_stock_files()   → (path_komponenty, path_magazynowy)  # najnowsze wg mtime
read_stock_file(path)       → DataFrame  # header=2, skip row 0 (nagłówek powtórzony)
clean_stock_data(df)        → DataFrame  # rename kolumn, konwersje typów
merge_stock_files(df1, df2) → DataFrame  # pd.concat, reset_index
apply_mapping(df, mapping)  → DataFrame  # Mapp1 + Mapp2
calculate_aging(df, date)   → DataFrame  # przedziały wiekowe
calculate_reserves(df)      → DataFrame  # % rezerwy × wartość mag.
save_to_sqlite(df)          → None       # tabela stock_data w stock_dashboard.db
```

**Rename map kolumn (po normalize):**
```
index_materialowy     → material_index
magazyn               → warehouse
typ_surowca           → material_type
data_przyjecia        → receipt_date
wartosc_mag           → stock_value
nazwa_materialu       → material_name
```

**Dodane kolumny obliczane:**
- `rodzaj_indeksu` — PROWAX / NON PROWAX (z Mapp1)
- `type_of_materials` — RW / WIP / FG / UNMAPPED (z Mapp2, klucz: warehouse + material_type)
- `aging_bucket` — 0-3 mcy / 3-6 mcy / 6-9 mcy / 9-12 mcy / pow 12 mcy / błąd daty
- `reserve_pct` — procent rezerwy (float)
- `reserve_amount` — stock_value × reserve_pct
- `status` — nowa / nabyta / do weryfikacji (wg daty przyjęcia vs Nov/Dec 2023)
- `analysis_date` — data analizy (zapisana razem z danymi)

**Tabela rezerw:**

| type_of_materials | 0-3 mcy | 3-6 mcy | 6-9 mcy | 9-12 mcy | pow 12 mcy |
|-------------------|---------|---------|---------|----------|------------|
| RW                | 0%      | 0%      | 0%      | 50%      | 100%       |
| WIP               | 0%      | 50%     | 100%    | 100%     | 100%       |
| FG                | 0%      | 0%      | 100%    | 100%     | 100%       |
| UNMAPPED          | 0%      | 0%      | 0%      | 0%       | 0%         |

---

## `data_refresh_stock.py`

Wzorzec identyczny z `data_refresh.py`:
- `STATUS_PATH = database/stock_refresh_status.json`
- `DAILY_REFRESH_HOUR = 10`
- `CHECK_INTERVAL_SECONDS = 15 * 60`
- `run_refresh_stock(force=False)` — sprawdza czy refresh należny, uruchamia download + import
- `start_daily_refresh_stock()` — startuje wątek daemon
- Obsługa wygasłej sesji: wywołuje `save_login.py` i ponawia

---

## `data/default_mapping.xlsx`

Skopiowany z repozytorium `moniams1234/inventory_app2` (`data/default_mapping.xlsx`).

Arkusz **Mapp1** — kolumna A: Index materiałowy → kolumna B: PROWAX / NON PROWAX
Arkusz **Mapp2** — klucz: Magazyn + Typ surowca → Type of materials (RW / WIP / FG)

---

## `pages/Otiocon_Stock.py` — układ

### Inicjalizacja
- `st.set_page_config(layout="wide")` + ciemne tło (CSS identyczne jak inne strony)
- Start wątku `start_daily_refresh_stock()` przy pierwszym wejściu (st.session_state guard)

### Pasek statusu (góra)
- Stan sync z `stock_refresh_status.json`: ostatnia aktualizacja, liczba rekordów, błędy
- Przycisk "↻ Odśwież dane teraz" → `run_refresh_stock(force=True)`

### Panel mappingu (expander "⚙️ Mapping")
- Radio: **Domyślny** / **Wgraj własny**
- Domyślny:
  - Podgląd Mapp1 jako `st.dataframe` (kolapsowalne)
  - Podgląd Mapp2 jako `st.dataframe`
  - Przycisk "↓ Pobierz default_mapping.xlsx" (`st.download_button`)
- Własny: `st.file_uploader` (xlsx, arkusze Mapp1 + Mapp2)

### Data analizy
- `st.date_input` — domyślnie: dziś
- Wiekowanie liczone od tej daty (nie od daty importu)

### KPI (4 karty)
1. Łączna wartość magazynowa [PLN]
2. Łączna kwota rezerwy [PLN]
3. % rezerwy (rezerwa / wartość)
4. Liczba aktywnych pozycji

### Wykresy (2 kolumny)
- **Pie** — PROWAX vs NON PROWAX (wartość magazynowa)
- **Stacked bar** — struktura wiekowa per typ materiału (RW/WIP/FG)
- **Horizontal bar** — wartość mag. vs rezerwa, top 10 magazynów
- **Bar** — rezerwa per RW/WIP/FG

### Zakładki danych
- **Szczegóły** — pełna tabela z filtrem (magazyn, typ, rodzaj indeksu, przedział wiekowy)
- **Podsumowanie** — pivot: Magazyn × Type of materials × Rodzaj indeksu, sumy wartości i rezerw

### Export
- Przycisk "↓ Eksport Excel" — plik `.xlsx` z dwoma arkuszami: Szczegóły + Podsumowanie

### Przycisk powrotu
- "← Wróć do menu" → `st.switch_page("app.py")`

---

## Obsługa błędów

- Brak `myprint_login.json` → komunikat "Uruchom save_login.py"
- Brak plików stock w `downloads/` → komunikat z instrukcją ręcznego pobrania
- Brak bazy `stock_dashboard.db` → komunikat + przycisk "Odśwież dane teraz"
- UNMAPPED pozycje w mappingu → wyświetlane w tabeli z oznaczeniem, nie blokują działania
- Błędy dat (`błąd daty`) → pozycje oznaczone w tabeli, reserve_pct = 0

---

## Co NIE wchodzi w zakres

- Historia stanów magazynowych między dniami (tylko ostatni import)
- Notyfikacje email/push o błędach sync
- Porównania R/R dla magazynu (to jest w Sales)
- Automatyczna aktualizacja mappingu z zewnętrznego źródła
