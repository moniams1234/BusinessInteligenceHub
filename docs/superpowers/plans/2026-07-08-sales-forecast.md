# Sales Forecast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dodać zakładkę "Prognoza" w Sales Dashboard z prognozą sprzedaży na 3 miesiące, opartą na trendzie liniowym i dekompozycji sezonowej STL.

**Architecture:** Nowy moduł `forecast.py` eksportuje czystą funkcję `compute_forecast()` — bez efektów ubocznych, łatwą do izolowanego testowania. `Sales.py` importuje ją, owija `@st.cache_data` i renderuje nowy czwarty tab z 3 KPI + wykresem Plotly.

**Tech Stack:** Python, Streamlit, Plotly (graph_objects), NumPy (polyfit), statsmodels (STL), pandas

## Global Constraints

- Aplikacja jest dwujęzyczna: każdy nowy string musi trafić do `TRANSLATIONS["PL"]` i `TRANSLATIONS["EN"]` w `pages/Sales.py`
- Kolory zgodne z paletą projektu: niebieski `#2563EB`, szary `#94A3B8`, fioletowy `#8B5CF6`
- Prognoza działa na `dimension_filtered` (filtry wymiarów, bez zakresu dat) — nie na `filtered`
- STL wymaga ≥ 24 miesięcy danych; poniżej tej wartości tylko trend liniowy
- Trend liniowy wymaga ≥ 3 miesięcy danych; poniżej — pusty DataFrame i `st.info`
- Dane z zerową sumą sprzedaży traktowane jak brak danych
- Brak automatycznych testów pytest (poza zakresem specyfikacji)

---

## File Map

| Plik | Akcja | Odpowiedzialność |
|---|---|---|
| `requirements.txt` | Modify | Dodaj `statsmodels`, `numpy` |
| `forecast.py` | Create | Logika `compute_forecast()` — trend + STL |
| `pages/Sales.py` | Modify | Import, tłumaczenia, 4. tab, KPI, wykres |

---

## Task 1: Dodaj zależności do requirements.txt

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `statsmodels` i `numpy` dostępne do importu w środowisku

- [ ] **Step 1: Dodaj pakiety do requirements.txt**

Otwórz `requirements.txt` i dopisz dwie linie (zachowaj resztę bez zmian):

```
streamlit
pandas
plotly
playwright
openpyxl
xlrd
xlsxwriter
pytest
statsmodels
numpy
```

- [ ] **Step 2: Zainstaluj pakiety**

```
pip install statsmodels numpy
```

Oczekiwany wynik: instalacja bez błędów.

- [ ] **Step 3: Zweryfikuj importy**

```
python -c "import statsmodels; import numpy; from statsmodels.tsa.seasonal import STL; print('OK')"
```

Oczekiwany wynik: `OK`

- [ ] **Step 4: Commit**

```
git add requirements.txt
git commit -m "feat: add statsmodels and numpy for sales forecasting"
```

---

## Task 2: Utwórz forecast.py

**Files:**
- Create: `forecast.py` (w katalogu głównym projektu, obok `app.py`)

**Interfaces:**
- Produces: `compute_forecast(monthly_df: pd.DataFrame, horizon: int = 3) -> pd.DataFrame`
  - Wejście: DataFrame z kolumnami `month_name` (str `YYYY-MM`) i `sales_pln` (float), posortowany rosnąco
  - Wyjście: DataFrame z kolumnami `month_name`, `sales_pln`, `trend_forecast`, `stl_forecast`, `is_forecast`
  - Gdy < 3 mies. lub suma = 0: zwraca pusty DataFrame z tymi samymi kolumnami

- [ ] **Step 1: Utwórz plik forecast.py z pełną implementacją**

Utwórz plik `forecast.py` w katalogu głównym projektu:

```python
import numpy as np
import pandas as pd

_EMPTY_COLS = ["month_name", "sales_pln", "trend_forecast", "stl_forecast", "is_forecast"]


def compute_forecast(monthly_df: pd.DataFrame, horizon: int = 3) -> pd.DataFrame:
    df = monthly_df[["month_name", "sales_pln"]].copy().sort_values("month_name").reset_index(drop=True)

    if len(df) < 3 or df["sales_pln"].sum() == 0:
        return pd.DataFrame(columns=_EMPTY_COLS)

    y = df["sales_pln"].values.astype(float)
    x = np.arange(len(df), dtype=float)

    # --- Linear trend ---
    slope, intercept = np.polyfit(x, y, deg=1)
    future_x = np.arange(len(df), len(df) + horizon, dtype=float)
    trend_values = (slope * future_x + intercept).tolist()

    # --- Future month labels ---
    last_period = pd.Period(df["month_name"].iloc[-1], freq="M")
    future_months = [(last_period + i + 1).strftime("%Y-%m") for i in range(horizon)]

    # --- STL ---
    stl_values = [float("nan")] * horizon
    if len(df) >= 24:
        try:
            from statsmodels.tsa.seasonal import STL

            series = pd.Series(y, dtype=float)
            stl_result = STL(series, period=12).fit()
            trend_comp = stl_result.trend
            seasonal_comp = stl_result.seasonal

            recent = trend_comp.iloc[-3:]
            trend_slope = (recent.iloc[-1] - recent.iloc[0]) / max(len(recent) - 1, 1)

            for i in range(horizon):
                seasonal_idx = len(df) - 12 + i
                seasonal_val = seasonal_comp.iloc[seasonal_idx] if 0 <= seasonal_idx < len(seasonal_comp) else 0.0
                trend_val = trend_comp.iloc[-1] + trend_slope * (i + 1)
                stl_values[i] = trend_val + seasonal_val
        except Exception:
            stl_values = [float("nan")] * horizon

    # --- Assemble output ---
    history = df.copy()
    history["trend_forecast"] = float("nan")
    history["stl_forecast"] = float("nan")
    history["is_forecast"] = False

    forecast_rows = pd.DataFrame({
        "month_name": future_months,
        "sales_pln": float("nan"),
        "trend_forecast": trend_values,
        "stl_forecast": stl_values,
        "is_forecast": True,
    })

    return pd.concat([history, forecast_rows], ignore_index=True)
```

- [ ] **Step 2: Ręczna weryfikacja z danymi syntetycznymi**

```
python -c "
import pandas as pd
from forecast import compute_forecast

# Test 1: puste wyjscie gdy < 3 mies.
df_short = pd.DataFrame({'month_name': ['2026-01', '2026-02'], 'sales_pln': [1000.0, 2000.0]})
result = compute_forecast(df_short)
assert result.empty, 'Powinno byc puste dla < 3 mies.'

# Test 2: trend dla 12 mies.
months = [f'2025-{i:02d}' for i in range(1, 13)]
sales = [10000.0 + i * 500 for i in range(12)]
df_12 = pd.DataFrame({'month_name': months, 'sales_pln': sales})
result2 = compute_forecast(df_12, horizon=3)
assert len(result2) == 15, f'Oczekiwano 15 wierszy, otrzymano {len(result2)}'
assert result2['is_forecast'].sum() == 3
assert result2['stl_forecast'].isna().all(), 'STL powinno byc NaN dla < 24 mies.'
assert not result2['trend_forecast'].iloc[12:].isna().any(), 'Trend nie powinien byc NaN w prognozie'

# Test 3: suma zerowa -> pusty
df_zero = pd.DataFrame({'month_name': months, 'sales_pln': [0.0]*12})
result3 = compute_forecast(df_zero)
assert result3.empty, 'Powinno byc puste gdy suma=0'

print('Wszystkie testy przeszly OK')
"
```

Oczekiwany wynik: `Wszystkie testy przeszly OK`

- [ ] **Step 3: Commit**

```
git add forecast.py
git commit -m "feat: add forecast.py with linear trend and STL decomposition"
```

---

## Task 3: Dodaj tłumaczenia do Sales.py

**Files:**
- Modify: `pages/Sales.py` (sekcja `TRANSLATIONS`, linie 26–139)

**Interfaces:**
- Consumes: istniejący słownik `TRANSLATIONS` z kluczami dla PL i EN
- Produces: 8 nowych kluczy dostępnych przez `T["klucz"]` w obu językach

- [ ] **Step 1: Dodaj klucze PL do TRANSLATIONS["PL"]**

W bloku `"PL": { ... }` przed zamykającym `}` (po linii z `"back_home"`) dopisz:

```python
        "tab_forecast": "📈 Prognoza",
        "forecast_kpi_label": "Prognoza {month}",
        "forecast_chart_title": "Prognoza sprzedaży na 3 miesiące",
        "forecast_history_label": "Historia",
        "forecast_trend_label": "Prognoza (trend)",
        "forecast_stl_label": "Prognoza (sezonowa)",
        "forecast_no_data": "Za mało danych do prognozy (min. 3 miesiące).",
        "forecast_no_stl": "Za mało historii dla dekompozycji sezonowej (min. 24 miesiące). Wyświetlono tylko prognozę trendową.",
```

- [ ] **Step 2: Dodaj klucze EN do TRANSLATIONS["EN"]**

W bloku `"EN": { ... }` przed zamykającym `}` (po linii z `"back_home"`) dopisz:

```python
        "tab_forecast": "📈 Forecast",
        "forecast_kpi_label": "Forecast {month}",
        "forecast_chart_title": "3-month sales forecast",
        "forecast_history_label": "History",
        "forecast_trend_label": "Forecast (trend)",
        "forecast_stl_label": "Forecast (seasonal)",
        "forecast_no_data": "Insufficient data for forecast (min. 3 months).",
        "forecast_no_stl": "Insufficient history for seasonal decomposition (min. 24 months). Showing trend forecast only.",
```

- [ ] **Step 3: Zweryfikuj że aplikacja nadal się uruchamia**

```
python -c "import ast, sys; ast.parse(open('pages/Sales.py', encoding='utf-8').read()); print('Syntax OK')"
```

Oczekiwany wynik: `Syntax OK`

- [ ] **Step 4: Commit**

```
git add pages/Sales.py
git commit -m "feat: add forecast translation keys to Sales.py TRANSLATIONS"
```

---

## Task 4: Dodaj zakładkę Prognoza do Sales.py

**Files:**
- Modify: `pages/Sales.py`

**Interfaces:**
- Consumes:
  - `compute_forecast(monthly_df, horizon=3) -> pd.DataFrame` z `forecast.py`
  - `dimension_filtered` — DataFrame z kolumnami `month_name`, `sales_pln`, `invoice_date` (już obliczony w Sales.py)
  - `T` — słownik tłumaczeń z kluczami dodanymi w Task 3
  - `format_compact_pln(value: float) -> str` — już zdefiniowany w Sales.py
  - `_delta_pln(current, previous) -> str | None` — już zdefiniowany w Sales.py
  - `chart_layout(figure, height) -> figure` — już zdefiniowana w Sales.py
- Produces: czwarta zakładka `📈 Prognoza / Forecast` z KPI i wykresem

- [ ] **Step 1: Dodaj importy na górze Sales.py**

Na początku pliku, po istniejących importach (po linii `from data_refresh import ...`), dopisz obie linie:

```python
import plotly.graph_objects as go
from forecast import compute_forecast
```

- [ ] **Step 2: Dodaj helper _cached_forecast po funkcji format_compact_pln**

Po bloku funkcji `chart_layout` (ok. linia 288), przed `initialize_refresh_worker()`, dopisz:

```python
@st.cache_data
def _cached_forecast(monthly_key: tuple, horizon: int = 3) -> pd.DataFrame:
    monthly_df = pd.DataFrame(list(monthly_key), columns=["month_name", "sales_pln"])
    return compute_forecast(monthly_df, horizon)
```

- [ ] **Step 3: Rozszerz st.tabs o czwarty tab**

Znajdź linię (ok. 543):
```python
overview_tab, trends_tab, details_tab = st.tabs(
    [T["tab_overview"], T["tab_trends"], T["tab_details"]]
)
```

Zastąp ją:
```python
overview_tab, trends_tab, details_tab, forecast_tab = st.tabs(
    [T["tab_overview"], T["tab_trends"], T["tab_details"], T["tab_forecast"]]
)
```

- [ ] **Step 4: Dodaj zawartość forecast_tab na końcu pliku (po bloku with details_tab)**

Na końcu pliku `pages/Sales.py`, po ostatnim bloku `with details_tab: ...`, dopisz:

```python
with forecast_tab:
    monthly_agg = (
        dimension_filtered
        .dropna(subset=["invoice_date"])
        .groupby("month_name", as_index=False)["sales_pln"]
        .sum()
        .sort_values("month_name")
    )
    monthly_key = tuple(zip(monthly_agg["month_name"], monthly_agg["sales_pln"]))
    forecast_df = _cached_forecast(monthly_key, horizon=3)

    if forecast_df.empty:
        st.info(T["forecast_no_data"])
    else:
        forecast_rows = forecast_df[forecast_df["is_forecast"]].reset_index(drop=True)
        history_rows = forecast_df[~forecast_df["is_forecast"]]
        stl_available = not forecast_rows["stl_forecast"].isna().all()

        if not stl_available:
            st.info(T["forecast_no_stl"])

        # KPI — 3 metryki
        kpi_cols = st.columns(3)
        for i, col in enumerate(kpi_cols):
            if i >= len(forecast_rows):
                break
            row = forecast_rows.iloc[i]
            trend_val = row["trend_forecast"]
            stl_val = row["stl_forecast"]
            forecast_val = (trend_val + stl_val) / 2 if not pd.isna(stl_val) else trend_val
            month_label = row["month_name"]
            same_month_prev_year = (pd.Period(month_label, freq="M") - 12).strftime("%Y-%m")
            prev_sales = dimension_filtered[
                dimension_filtered["month_name"] == same_month_prev_year
            ]["sales_pln"].sum()
            col.metric(
                T["forecast_kpi_label"].format(month=month_label),
                format_compact_pln(forecast_val),
                delta=_delta_pln(forecast_val, prev_sales),
            )

        # Wykres
        display_history = history_rows.tail(18)
        last_hist_month = display_history["month_name"].iloc[-1]
        last_hist_val = display_history["sales_pln"].iloc[-1]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=display_history["month_name"],
            y=display_history["sales_pln"],
            mode="lines+markers",
            name=T["forecast_history_label"],
            line=dict(color="#2563EB", width=2.5),
            marker=dict(size=5),
            hovertemplate="%{x}<br><b>%{y:,.0f} PLN</b><extra></extra>",
        ))

        trend_x = [last_hist_month] + list(forecast_rows["month_name"])
        trend_y = [last_hist_val] + list(forecast_rows["trend_forecast"])
        fig.add_trace(go.Scatter(
            x=trend_x,
            y=trend_y,
            mode="lines+markers",
            name=T["forecast_trend_label"],
            line=dict(color="#94A3B8", width=2, dash="dash"),
            marker=dict(size=6, symbol="diamond"),
            hovertemplate="%{x}<br><b>%{y:,.0f} PLN</b><extra></extra>",
        ))

        if stl_available:
            stl_x = [last_hist_month] + list(forecast_rows["month_name"])
            stl_y = [last_hist_val] + list(forecast_rows["stl_forecast"])
            fig.add_trace(go.Scatter(
                x=stl_x,
                y=stl_y,
                mode="lines+markers",
                name=T["forecast_stl_label"],
                line=dict(color="#8B5CF6", width=2, dash="dash"),
                marker=dict(size=6, symbol="circle-open"),
                hovertemplate="%{x}<br><b>%{y:,.0f} PLN</b><extra></extra>",
            ))

        fig.add_vline(
            x=last_hist_month,
            line_dash="dot",
            line_color="#CBD5E1",
            line_width=1.5,
        )
        fig.update_layout(
            title=T["forecast_chart_title"],
            xaxis_title=T["axis_month"],
            yaxis_title=T["axis_sales"],
            xaxis_type="category",
        )
        st.plotly_chart(chart_layout(fig), width="stretch")
```

- [ ] **Step 5: Zweryfikuj poprawność składni**

```
python -c "import ast; ast.parse(open('pages/Sales.py', encoding='utf-8').read()); print('Syntax OK')"
```

Oczekiwany wynik: `Syntax OK`

- [ ] **Step 6: Sprawdź wizualnie w przeglądarce**

Uruchom aplikację:
```
streamlit run app.py
```

Otwórz Sales Dashboard → tab "📈 Prognoza":
- Sprawdź czy widoczne są 3 metryki KPI z etykietami `Prognoza YYYY-MM`
- Sprawdź czy wykres pokazuje historię (niebieska linia) + prognozę trendu (szara przerywana)
- Jeśli mniej niż 24 miesięcy historii — powinien być widoczny info-box o braku STL
- Jeśli ≥ 24 miesięcy historii — powinna być widoczna fioletowa przerywana linia STL
- Sprawdź przełącznik językowy PL/EN — tab powinien zmienić etykietę na "📈 Forecast"

- [ ] **Step 7: Commit**

```
git add pages/Sales.py
git commit -m "feat: add Prognoza tab with linear trend and STL forecast to Sales Dashboard"
```
