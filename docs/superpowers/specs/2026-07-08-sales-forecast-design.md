# Sales Forecast — Design Spec

**Data:** 2026-07-08  
**Zakres:** Prognozowanie sprzedaży w zakładce Sales aplikacji Business Intelligence Hub  
**Status:** Zatwierdzony przez użytkownika

---

## 1. Cel

Dodanie zakładki "Prognoza" w dashboardzie sprzedażowym (`pages/Sales.py`), która na podstawie danych historycznych wyświetla prognozę sprzedaży na 3 miesiące do przodu. Prognoza uwzględnia aktywne filtry (klient, kraj, region itp.) i porównuje dwie metody: trend liniowy oraz dekompozycję sezonową STL.

---

## 2. Architektura

### Nowy plik: `forecast.py`

Zawiera jedną publiczną funkcję:

```python
def compute_forecast(monthly_df: pd.DataFrame, horizon: int = 3) -> pd.DataFrame
```

**Wejście:**
- `monthly_df` — DataFrame z kolumnami `month_name` (str, format `YYYY-MM`) i `sales_pln` (float), posortowany rosnąco po `month_name`
- `horizon` — liczba miesięcy prognozy (domyślnie 3)

**Wyjście:**
- DataFrame z kolumnami:
  - `month_name` — miesiąc (historia + prognoza)
  - `sales_pln` — rzeczywista sprzedaż (NaN dla miesięcy prognozy)
  - `trend_forecast` — prognoza trendu liniowego (NaN dla historii)
  - `stl_forecast` — prognoza STL (NaN dla historii lub gdy za mało danych)
  - `is_forecast` — bool, True dla miesięcy prognozy

### Modyfikacja: `pages/Sales.py`

- Import `compute_forecast` z `forecast.py`
- Dodanie czwartego taba `📈 Prognoza` / `📈 Forecast`
- Wywołanie `compute_forecast` z `@st.cache_data` (klucz = hash miesięcznych sum)
- Dodanie tłumaczeń do słownika `TRANSLATIONS`

### Modyfikacja: `requirements.txt`

Dodanie:
- `statsmodels`
- `numpy`

---

## 3. Metody prognozowania

### 3a. Trend liniowy (zawsze dostępny, min. 3 miesiące danych)

1. Reprezentacja miesięcy jako indeksów całkowitych (0, 1, 2, …)
2. `numpy.polyfit(x, y, deg=1)` — dopasowanie prostej regresji
3. Ekstrapolacja na kolejne `horizon` miesięcy

### 3b. Dekompozycja STL (wymaga ≥ 24 miesięcy danych)

1. `statsmodels.tsa.seasonal.STL(series, period=12).fit()`
2. Komponent trendu z ostatnich obserwacji + komponent sezonowy z poprzedniego roku
3. Prognoza = trend_slope × horizon_step + seasonal_component

Jeśli STL rzuci wyjątek: `try/except`, fallback do samego trendu, ostrzeżenie w `st.warning`.

---

## 4. UI — zakładka Prognoza

### 4a. Struktura tabów

```
[Przegląd klientów] [Porównanie R/R] [Dane źródłowe] [📈 Prognoza]
```

### 4b. KPI — 3 metryki

Jeden rząd z trzema metrykami:
- **Prognoza M+1** — wartość z trendu liniowego (i STL jeśli dostępne: średnia obu)
- **Prognoza M+2**
- **Prognoza M+3**
- Delta: vs analogiczny miesiąc rok temu z rzeczywistych danych historycznych

### 4c. Wykres liniowy Plotly

- `———` niebieski (`#2563EB`) — historia (ostatnie 18 miesięcy)
- `- - -` szary (`#94A3B8`) — prognoza: trend liniowy
- `- - -` fioletowy (`#8B5CF6`) — prognoza: STL (tylko gdy ≥ 24 mies. danych)
- Pionowa linia przerywana oddzielająca historię od prognozy
- Tooltip: wartość PLN + etykieta metody

### 4d. Info-box (warunkowo)

Gdy < 24 miesięcy danych:
> PL: "Za mało historii dla dekompozycji sezonowej (min. 24 miesiące). Wyświetlono tylko prognozę trendową."  
> EN: "Insufficient history for seasonal decomposition (min. 24 months). Showing trend forecast only."

---

## 5. Obsługa edge case'ów

| Sytuacja | Zachowanie |
|---|---|
| < 3 miesięcy danych | `compute_forecast` zwraca pusty DataFrame; tab pokazuje `st.info` z komunikatem |
| 3–23 miesiące danych | Tylko trend liniowy; `stl_forecast` = NaN; info-box o braku STL |
| ≥ 24 miesiące danych | Obie metody — trend + STL |
| Filtered data = 0 PLN wszystkich miesięcy | Traktowane jak brak danych |
| STL rzuci wyjątek | `try/except`, fallback do trendu + `st.warning` |

---

## 6. Tłumaczenia (nowe klucze w TRANSLATIONS)

| Klucz | PL | EN |
|---|---|---|
| `tab_forecast` | `📈 Prognoza` | `📈 Forecast` |
| `forecast_kpi_label` | `Prognoza {month}` | `Forecast {month}` |
| `forecast_chart_title` | `Prognoza sprzedaży na 3 miesiące` | `3-month sales forecast` |
| `forecast_history_label` | `Historia` | `History` |
| `forecast_trend_label` | `Prognoza (trend)` | `Forecast (trend)` |
| `forecast_stl_label` | `Prognoza (sezonowa)` | `Forecast (seasonal)` |
| `forecast_no_data` | `Za mało danych do prognozy (min. 3 miesiące).` | `Insufficient data for forecast (min. 3 months).` |
| `forecast_no_stl` | `Za mało historii dla dekompozycji sezonowej (min. 24 miesiące). Wyświetlono tylko prognozę trendową.` | `Insufficient history for seasonal decomposition (min. 24 months). Showing trend forecast only.` |

---

## 7. Caching

Wywołanie `compute_forecast` opakowane w `@st.cache_data` po stronie `Sales.py`. Klucz cache zależy od:
- Sumarycznej sprzedaży miesięcznej (zmienia się po odświeżeniu danych)
- Aktywnych filtrów (klient, kraj, region, waluta, typ faktury)

Cache automatycznie unieważniany przy `st.cache_data.clear()` po manualnym odświeżeniu danych.

---

## 8. Poza zakresem

- Prognoza per-klient (tylko łączna sprzedaż z filtrów)
- Eksport prognozy do CSV
- Edytowalne parametry STL (period, seasonal)
- Testy automatyczne `forecast.py`
