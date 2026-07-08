# Daily Sales Summary — Design Spec

**Data:** 2026-07-08  
**Zakres:** Podsumowanie dziennej sprzedaży w zakładce Sales aplikacji Business Intelligence Hub  
**Status:** Zatwierdzony przez użytkownika

---

## 1. Cel

Dodanie ekspandera "Sprzedaż dziś" w Sales Dashboard, pokazującego dzisiejszą sprzedaż netto w podziale na klientów. Ekspander pojawia się między sekcją KPI a istniejącym ekspanderem "Dane aktualne" (bieżący miesiąc).

---

## 2. Architektura

Wyłącznie modyfikacja `pages/Sales.py` — brak nowych plików, brak nowych zależności.

---

## 3. UI

### Pozycja

```
[KPI: Sprzedaż miesiąca] [KPI: YTD] [KPI: Rok poprzedni]

▼ Sprzedaż dziś · DD.MM.YYYY          ← NOWY ekspander (domyślnie rozwinięty)
  [tabela dzienna]

▼ Dane aktualne · DD.MM–DD.MM.YYYY    ← istniejący ekspander (bez zmian)
  [tabela miesięczna]
```

### Zawartość ekspandera

Tabela `st.dataframe` z kolumnami:
- `customer` — nazwa klienta (`TextColumn`)
- `sales_pln` — sprzedaż netto PLN (`NumberColumn`, format `"%.2f PLN"`)
- `invoice_count` — liczba unikalnych faktur (`NumberColumn`, format `"%d"`)
- `share` — udział % w sprzedaży dnia (`ProgressColumn`, format `"%.1f%%"`, min 0, max 100)

Sortowanie: malejąco wg `sales_pln`.

### Źródło danych

`dimension_filtered` (filtry wymiarów bez zakresu dat) — filtrowane do `DATE(invoice_date) = today`.

### Stan pusty

Gdy brak faktur na dziś: `st.info(T["no_today_sales"])`.

---

## 4. Tłumaczenia (nowe klucze)

| Klucz | PL | EN |
|---|---|---|
| `today_expander` | `Sprzedaż dziś · {date}` | `Today's sales · {date}` |
| `no_today_sales` | `Brak faktur dla dzisiejszej daty ({date}).` | `No invoices for today ({date}).` |

---

## 5. Poza zakresem

- Porównanie z wczoraj
- Wykres
- Eksport CSV dziennego
