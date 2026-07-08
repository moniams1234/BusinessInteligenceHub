import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from data_refresh import get_refresh_status, run_refresh, start_daily_refresh
import plotly.graph_objects as go
from forecast import compute_forecast


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "sales_dashboard.db"
TABLE_NAME = "sales_invoices"
AUTO_RELOAD_MS = 5 * 60 * 1000
PRIMARY = "#2563EB"
ACCENT = "#0EA5A4"
PALETTE = ["#2563EB", "#0EA5A4", "#F59E0B", "#8B5CF6", "#EF4444"]
ISO2_TO_ISO3 = {
    "AT": "AUT", "AU": "AUS", "BE": "BEL", "CH": "CHE", "CN": "CHN",
    "DE": "DEU", "DK": "DNK", "ES": "ESP", "FR": "FRA", "GB": "GBR",
    "IE": "IRL", "MK": "MKD", "NL": "NLD", "PH": "PHL", "PL": "POL",
    "SE": "SWE", "VN": "VNM",
}

TRANSLATIONS = {
    "PL": {
        "subtitle": "Centrum analizy sprzedaży",
        "no_local_db": "brak lokalnej bazy",
        "sync_error_title": "Nie udało się pobrać nowych danych",
        "sync_error_db": "Lokalna baza:",
        "sync_running": "Trwa pobieranie danych…",
        "sync_ok": "Dane aktualne",
        "refresh_btn": "↻ Odśwież dane teraz",
        "syncing": "Synchronizacja z MyPrint…",
        "sync_done": "Dane zostały odświeżone",
        "sync_failed": "Synchronizacja nie powiodła się",
        "sync_unknown_err": "Nieznany błąd synchronizacji",
        "filters": "### Filtry",
        "date_range": "Zakres dat",
        "customer": "Klient",
        "region": "Region",
        "country": "Kraj",
        "currency": "Waluta",
        "invoice_type": "Typ faktury",
        "no_db_error": "Brak lokalnej bazy danych. Sprawdź sesję MyPrint i użyj 'Odśwież dane teraz'.",
        "no_data_warning": "Baza nie zawiera danych sprzedażowych do wyświetlenia.",
        "caption": "Sprzedaż netto z MyPrint  ·  dane do {max_date}  ·  {count} pozycji po filtracji",
        "no_filtered": "Brak danych spełniających wybrane kryteria.",
        "kpi_month": "Sprzedaż {month}",
        "kpi_ytd": "Sprzedaż YTD {year}",
        "kpi_prev_year": "Sprzedaż {year}",
        "vs_last_year": "vs rok temu",
        "current_data_expander": "Dane aktualne · {from_date}–{to_date}",
        "no_current_month": "Brak faktur dla bieżącego miesiąca ({month}).",
        "col_customer": "Klient",
        "col_sales": "Sprzedaż netto",
        "col_invoices": "Liczba faktur",
        "col_avg": "Średnia faktura",
        "col_share": "Udział w sprzedaży",
        "chart_monthly": "Sprzedaż miesięczna",
        "axis_month": "Miesiąc",
        "axis_sales": "Sprzedaż netto (PLN)",
        "tab_overview": "Przegląd klientów",
        "tab_trends": "Porównanie rok do roku",
        "tab_details": "Dane źródłowe",
        "ranking_slider": "Liczba klientów w rankingu",
        "top_customers_title": "TOP {n} klientów",
        "map_title": "Heat mapa sprzedaży według kraju",
        "yoy_info": "Analiza R/R korzysta z pełnej historii i nie zależy od zakresu dat.",
        "all_customers": "— Wszyscy klienci —",
        "comparison_month": "Miesiąc porównania",
        "yoy_monthly_title": "Wybrany miesiąc R/R",
        "yoy_ytd_title": "Sprzedaż YTD R/R",
        "axis_year": "Rok",
        "col_date": "Data",
        "col_net": "Netto PLN",
        "col_gross": "Brutto PLN",
        "download_csv": "↓ Pobierz CSV",
        "lang_label": "Język / Language",
        "back_home": "← Menu główne",
        "tab_forecast": "📈 Prognoza",
        "forecast_kpi_label": "Prognoza {month}",
        "forecast_chart_title": "Prognoza sprzedaży na 3 miesiące",
        "forecast_history_label": "Historia",
        "forecast_trend_label": "Prognoza (trend)",
        "forecast_stl_label": "Prognoza (sezonowa)",
        "forecast_no_data": "Za mało danych do prognozy (min. 3 miesiące).",
        "forecast_no_stl": "Prognoza sezonowa niedostępna. Wyświetlono tylko prognozę trendową.",
        "today_expander": "Sprzedaż dziś · {date}",
        "no_today_sales": "Brak faktur dla dzisiejszej daty ({date}).",
        "kpi_today": "Sprzedaż dziś {date}",
    },
    "EN": {
        "subtitle": "Sales Analysis Center",
        "no_local_db": "no local database",
        "sync_error_title": "Failed to fetch new data",
        "sync_error_db": "Local database:",
        "sync_running": "Fetching data…",
        "sync_ok": "Data up to date",
        "refresh_btn": "↻ Refresh data now",
        "syncing": "Syncing with MyPrint…",
        "sync_done": "Data refreshed",
        "sync_failed": "Sync failed",
        "sync_unknown_err": "Unknown sync error",
        "filters": "### Filters",
        "date_range": "Date range",
        "customer": "Customer",
        "region": "Region",
        "country": "Country",
        "currency": "Currency",
        "invoice_type": "Invoice type",
        "no_db_error": "No local database. Check MyPrint session and use 'Refresh data now'.",
        "no_data_warning": "Database contains no sales data to display.",
        "caption": "Net sales from MyPrint  ·  data until {max_date}  ·  {count} items after filtering",
        "no_filtered": "No data matching the selected criteria.",
        "kpi_month": "Sales {month}",
        "kpi_ytd": "Sales YTD {year}",
        "kpi_prev_year": "Sales {year}",
        "vs_last_year": "vs last year",
        "current_data_expander": "Current data · {from_date}–{to_date}",
        "no_current_month": "No invoices for current month ({month}).",
        "col_customer": "Customer",
        "col_sales": "Net sales",
        "col_invoices": "Invoice count",
        "col_avg": "Avg. invoice",
        "col_share": "Sales share",
        "chart_monthly": "Monthly sales",
        "axis_month": "Month",
        "axis_sales": "Net sales (PLN)",
        "tab_overview": "Customer overview",
        "tab_trends": "Year-over-year",
        "tab_details": "Source data",
        "ranking_slider": "Number of customers in ranking",
        "top_customers_title": "TOP {n} customers",
        "map_title": "Sales heat map by country",
        "yoy_info": "YoY analysis uses full history and is not affected by the date range.",
        "all_customers": "— All customers —",
        "comparison_month": "Comparison month",
        "yoy_monthly_title": "Selected month YoY",
        "yoy_ytd_title": "YTD sales YoY",
        "axis_year": "Year",
        "col_date": "Date",
        "col_net": "Net PLN",
        "col_gross": "Gross PLN",
        "download_csv": "↓ Download CSV",
        "lang_label": "Język / Language",
        "back_home": "← Main menu",
        "tab_forecast": "📈 Forecast",
        "forecast_kpi_label": "Forecast {month}",
        "forecast_chart_title": "3-month sales forecast",
        "forecast_history_label": "History",
        "forecast_trend_label": "Forecast (trend)",
        "forecast_stl_label": "Forecast (seasonal)",
        "forecast_no_data": "Insufficient data for forecast (min. 3 months).",
        "forecast_no_stl": "Seasonal forecast unavailable. Showing trend forecast only.",
        "today_expander": "Today's sales · {date}",
        "no_today_sales": "No invoices for today ({date}).",
        "kpi_today": "Today's sales {date}",
    },
}

st.set_page_config(
    page_title="MyPrint | Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] { display: none; }
        .stApp { background: #F5F7FB; }
        [data-testid="stSidebar"] { background: #0F172A; }
        [data-testid="stSidebar"] * { color: #E2E8F0; }
        [data-testid="stSidebar"] input { color: #0F172A; }
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-testid="stDateInput"] > div > div {
            background: rgba(255, 255, 255, .98);
            border: 1px solid rgba(148, 163, 184, .25);
            border-radius: 12px;
        }
        .block-container { max-width: 1500px; padding-top: 1.8rem; }
        h1, h2, h3 { color: #0F172A; letter-spacing: -0.02em; }
        [data-testid="stMetric"] {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 1rem 1.15rem;
            box-shadow: 0 4px 18px rgba(15, 23, 42, 0.05);
        }
        [data-testid="stMetricLabel"] { color: #64748B; }
        [data-testid="stMetricValue"] {
            color: #0F172A;
            font-size: clamp(1.45rem, 2vw, 2.25rem);
        }
        [data-testid="stMetric"], div[data-testid="stPlotlyChart"] {
            transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
        }
        [data-testid="stMetric"]:hover, div[data-testid="stPlotlyChart"]:hover {
            transform: translateY(-2px);
            border-color: #BFDBFE;
            box-shadow: 0 12px 30px rgba(37, 99, 235, 0.10);
        }
        div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: .35rem;
        }
        .sync-ok, .sync-error, .sync-running {
            border-radius: 10px;
            padding: .65rem .8rem;
            margin: .4rem 0 1rem;
            font-size: .86rem;
        }
        .sync-ok { background: #DCFCE7; color: #166534; }
        .sync-error { background: #FEE2E2; color: #991B1B; }
        .sync-running { background: #DBEAFE; color: #1E40AF; }
        button, [role="button"], [role="tab"], [data-baseweb="select"],
        [data-testid="stDateInput"], [data-testid="stSlider"],
        [data-testid="stDownloadButton"] { cursor: pointer !important; }
        [data-baseweb="select"]:hover, [data-testid="stDateInput"]:hover {
            filter: brightness(.97);
        }
        [role="tab"] { transition: color .2s ease, background .2s ease; }
        [role="tab"]:hover { color: #2563EB !important; }
        .stButton > button, .stDownloadButton > button {
            border: 0;
            border-radius: 11px;
            background: linear-gradient(135deg, #2563EB, #0EA5A4);
            color: white !important;
            font-weight: 700;
            box-shadow: 0 8px 20px rgba(37, 99, 235, .22);
            transition: transform .18s ease, box-shadow .18s ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 12px 26px rgba(37, 99, 235, .30);
        }
        [data-testid="stSelectbox"] *, [data-testid="stMultiSelect"] *,
        [data-testid="stDateInput"] *, [data-testid="stSlider"] *,
        [data-testid="stDataFrame"] [role="columnheader"],
        [role="option"], .stButton *, .stDownloadButton * {
            cursor: pointer !important;
        }
        div[data-testid="stExpander"] {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            box-shadow: 0 4px 18px rgba(15, 23, 42, .05);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def initialize_refresh_worker():
    return start_daily_refresh()


@st.cache_data(ttl=300)
def load_data(db_modified_at: float) -> pd.DataFrame:
    del db_modified_at
    with sqlite3.connect(DB_PATH) as connection:
        dataframe = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", connection)

    dataframe["invoice_date"] = pd.to_datetime(
        dataframe["invoice_date"], errors="coerce"
    )
    dataframe["sales_pln"] = pd.to_numeric(
        dataframe["sales_pln"], errors="coerce"
    ).fillna(0)
    dataframe["month_name"] = dataframe["invoice_date"].dt.strftime("%Y-%m")
    dataframe["year"] = dataframe["invoice_date"].dt.year
    dataframe["month"] = dataframe["invoice_date"].dt.month
    return dataframe


def format_pln(value: float) -> str:
    return f"{value:,.0f} PLN".replace(",", " ")


def format_number(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def format_compact_pln(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f} mln PLN".replace(".", ",")
    return format_pln(value)


def chart_layout(figure, height: int = 420):
    figure.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=65, b=25),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial", color="#334155"),
        title_font=dict(size=17, color="#0F172A"),
        legend_title_text="",
        hoverlabel=dict(bgcolor="white"),
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor="#E2E8F0", zeroline=False)
    return figure


@st.cache_data
def _cached_forecast(monthly_key: tuple, horizon: int = 3) -> pd.DataFrame:
    monthly_df = pd.DataFrame(list(monthly_key), columns=["month_name", "sales_pln"])
    return compute_forecast(monthly_df, horizon)


initialize_refresh_worker()

components.html(
    f"<script>setTimeout(() => window.parent.location.reload(), {AUTO_RELOAD_MS});</script>",
    height=0,
)

st.sidebar.markdown("## MyPrint")

lang = st.sidebar.radio(
    TRANSLATIONS["PL"]["lang_label"],
    options=["PL", "EN"],
    horizontal=True,
)
T = TRANSLATIONS[lang]

st.sidebar.caption(T["subtitle"])

if st.sidebar.button(T["back_home"], key="back_home"):
    st.switch_page("app.py")

st.sidebar.divider()

status = get_refresh_status()
state = status.get("state")
if state == "error":
    local_update = pd.to_datetime(DB_PATH.stat().st_mtime, unit="s").strftime(
        "%d.%m.%Y, %H:%M"
    ) if DB_PATH.exists() else T["no_local_db"]
    error_message = status.get("error") or (
        "Automatyczne pobieranie nie zwróciło szczegółów. "
        "Najczęściej oznacza to wygasłą sesję MyPrint."
    )
    st.sidebar.markdown(
        f'<div class="sync-error"><strong>{T["sync_error_title"]}</strong>'
        f'<br>{error_message}<br><small>{T["sync_error_db"]} {local_update}</small></div>',
        unsafe_allow_html=True,
    )
elif state == "running":
    st.sidebar.markdown(
        f'<div class="sync-running">{T["sync_running"]}</div>',
        unsafe_allow_html=True,
    )
elif status.get("last_success"):
    refreshed = pd.to_datetime(status["last_success"]).strftime("%d.%m.%Y, %H:%M")
    st.sidebar.markdown(
        f'<div class="sync-ok">{T["sync_ok"]}<br><strong>{refreshed}</strong></div>',
        unsafe_allow_html=True,
    )

if st.sidebar.button(T["refresh_btn"], width="stretch"):
    with st.sidebar.status(T["syncing"], expanded=True) as sync_status:
        result = run_refresh(force=True)
        if result.get("state") == "success":
            sync_status.update(label=T["sync_done"], state="complete")
            st.cache_data.clear()
            st.rerun()
        else:
            sync_status.update(label=T["sync_failed"], state="error")
            st.error(result.get("error", T["sync_unknown_err"]))

if not DB_PATH.exists():
    st.error(T["no_db_error"])
    st.stop()

df = load_data(DB_PATH.stat().st_mtime)
if df.empty or df["invoice_date"].dropna().empty:
    st.warning(T["no_data_warning"])
    st.stop()

min_date = df["invoice_date"].min().date()
max_date = df["invoice_date"].max().date()

st.sidebar.markdown(T["filters"])
date_range = st.sidebar.date_input(
    T["date_range"],
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)


def filter_options(column: str) -> list:
    if column not in df.columns:
        return []
    return sorted(value for value in df[column].dropna().unique() if str(value).strip())


customers = st.sidebar.multiselect(T["customer"], filter_options("customer"))
regions = st.sidebar.multiselect(T["region"], filter_options("region"))
countries = st.sidebar.multiselect(T["country"], filter_options("country"))
currencies = st.sidebar.multiselect(T["currency"], filter_options("currency"))
invoice_types = st.sidebar.multiselect(T["invoice_type"], filter_options("invoice_type"))

dimension_filtered = df.copy()
for column, selected in {
    "customer": customers,
    "region": regions,
    "country": countries,
    "currency": currencies,
    "invoice_type": invoice_types,
}.items():
    if selected and column in dimension_filtered.columns:
        dimension_filtered = dimension_filtered[dimension_filtered[column].isin(selected)]

filtered = dimension_filtered.copy()
if len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    filtered = filtered[filtered["invoice_date"].between(start_date, end_date)]

st.markdown("# Sales Dashboard")
st.caption(T["caption"].format(
    max_date=max_date.strftime("%d.%m.%Y"),
    count=format_number(len(filtered)),
))

if filtered.empty:
    st.info(T["no_filtered"])
    st.stop()

today = pd.Timestamp.now().normalize()
month_start = today.replace(day=1)
current_year = today.year
prev_year = current_year - 1
year_start = pd.Timestamp(current_year, 1, 1)

cur_month_sales = dimension_filtered[
    dimension_filtered["invoice_date"].between(month_start, today)
]["sales_pln"].sum()

prev_month_start = month_start.replace(year=prev_year)
prev_month_end = today.replace(year=prev_year)
prev_month_sales = dimension_filtered[
    dimension_filtered["invoice_date"].between(prev_month_start, prev_month_end)
]["sales_pln"].sum()

ytd_sales = dimension_filtered[
    dimension_filtered["invoice_date"].between(year_start, today)
]["sales_pln"].sum()

prev_ytd_end = today.replace(year=prev_year)
prev_ytd_sales = dimension_filtered[
    dimension_filtered["invoice_date"].between(
        pd.Timestamp(prev_year, 1, 1), prev_ytd_end
    )
]["sales_pln"].sum()

prev_year_sales = dimension_filtered[
    dimension_filtered["year"] == prev_year
]["sales_pln"].sum()

prev_prev_year_sales = dimension_filtered[
    dimension_filtered["year"] == prev_year - 1
]["sales_pln"].sum()

today_sales = dimension_filtered[
    dimension_filtered["invoice_date"].dt.date == today.date()
]["sales_pln"].sum()

prev_today_sales = dimension_filtered[
    dimension_filtered["invoice_date"].dt.date == today.date().replace(year=prev_year)
]["sales_pln"].sum()


def _delta_pln(current: float, previous: float) -> str | None:
    if previous == 0:
        return None
    diff = current - previous
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:,.0f} PLN {T['vs_last_year']}".replace(",", " ")


today_date_str = today.strftime("%d.%m.%Y")

kpi_columns = st.columns(4)
kpi_columns[0].metric(
    T["kpi_month"].format(month=today.strftime("%m.%Y")),
    format_compact_pln(cur_month_sales),
    delta=_delta_pln(cur_month_sales, prev_month_sales),
)
kpi_columns[1].metric(
    T["kpi_ytd"].format(year=current_year),
    format_compact_pln(ytd_sales),
    delta=_delta_pln(ytd_sales, prev_ytd_sales),
)
kpi_columns[2].metric(
    T["kpi_prev_year"].format(year=prev_year),
    format_compact_pln(prev_year_sales),
    delta=_delta_pln(prev_year_sales, prev_prev_year_sales),
)
kpi_columns[3].metric(
    T["kpi_today"].format(date=today_date_str),
    format_compact_pln(today_sales),
    delta=_delta_pln(today_sales, prev_today_sales),
)
today_data = dimension_filtered[
    dimension_filtered["invoice_date"].dt.date == today.date()
]

with st.expander(
    T["today_expander"].format(date=today_date_str),
    expanded=True,
):
    if today_data.empty:
        st.info(T["no_today_sales"].format(date=today_date_str))
    else:
        today_summary = (
            today_data.groupby("customer", as_index=False)
            .agg(
                sales_pln=("sales_pln", "sum"),
                invoice_count=("invoice_number", "nunique"),
            )
            .sort_values("sales_pln", ascending=False)
        )
        today_summary["share"] = (
            today_summary["sales_pln"] / today_summary["sales_pln"].sum() * 100
        )
        st.dataframe(
            today_summary,
            width="stretch",
            hide_index=True,
            column_config={
                "customer": st.column_config.TextColumn(T["col_customer"]),
                "sales_pln": st.column_config.NumberColumn(
                    T["col_sales"], format="%.2f PLN"
                ),
                "invoice_count": st.column_config.NumberColumn(
                    T["col_invoices"], format="%d"
                ),
                "share": st.column_config.ProgressColumn(
                    T["col_share"], format="%.1f%%", min_value=0, max_value=100
                ),
            },
        )

current_month_data = dimension_filtered[
    dimension_filtered["invoice_date"].between(month_start, today)
]
current_month_label = today.strftime("%m.%Y")

with st.expander(
    T["current_data_expander"].format(
        from_date=month_start.strftime("%d.%m.%Y"),
        to_date=today.strftime("%d.%m.%Y"),
    ),
    expanded=True,
):
    if current_month_data.empty:
        st.info(T["no_current_month"].format(month=current_month_label))
    else:
        current_summary = (
            current_month_data.groupby("customer", as_index=False)
            .agg(
                sales_pln=("sales_pln", "sum"),
                invoice_count=("invoice_number", "nunique"),
            )
            .sort_values("sales_pln", ascending=False)
        )
        current_summary["share"] = (
            current_summary["sales_pln"] / current_summary["sales_pln"].sum() * 100
        )
        current_summary["average_invoice"] = (
            current_summary["sales_pln"] / current_summary["invoice_count"]
        )
        st.dataframe(
            current_summary,
            width="stretch",
            hide_index=True,
            column_config={
                "customer": st.column_config.TextColumn(T["col_customer"]),
                "sales_pln": st.column_config.NumberColumn(
                    T["col_sales"], format="%.2f PLN"
                ),
                "invoice_count": st.column_config.NumberColumn(
                    T["col_invoices"], format="%d"
                ),
                "average_invoice": st.column_config.NumberColumn(
                    T["col_avg"], format="%.2f PLN"
                ),
                "share": st.column_config.ProgressColumn(
                    T["col_share"], format="%.1f%%", min_value=0, max_value=100
                ),
            },
        )

monthly_sales = (
    filtered.dropna(subset=["invoice_date"])
    .groupby("month_name", as_index=False)["sales_pln"]
    .sum()
    .sort_values("month_name")
)
monthly_figure = px.bar(
    monthly_sales,
    x="month_name",
    y="sales_pln",
    title=T["chart_monthly"],
    color_discrete_sequence=[PRIMARY],
)
monthly_figure.update_traces(
    marker=dict(line=dict(width=0)),
    hovertemplate="%{x}<br><b>%{y:,.0f} PLN</b><extra></extra>",
)
monthly_figure.update_layout(xaxis_title=T["axis_month"], yaxis_title=T["axis_sales"])
monthly_figure.update_xaxes(type="category")
st.plotly_chart(chart_layout(monthly_figure), width="stretch")

overview_tab, trends_tab, details_tab, forecast_tab = st.tabs(
    [T["tab_overview"], T["tab_trends"], T["tab_details"], T["tab_forecast"]]
)

with overview_tab:
    left, right = st.columns([1, 1.35])
    top_n = left.slider(T["ranking_slider"], 5, 30, 12)
    top_customers = (
        filtered.groupby("customer", as_index=False)["sales_pln"]
        .sum()
        .nlargest(top_n, "sales_pln")
        .sort_values("sales_pln")
    )
    top_figure = px.bar(
        top_customers,
        x="sales_pln",
        y="customer",
        orientation="h",
        title=T["top_customers_title"].format(n=top_n),
        color_discrete_sequence=[ACCENT],
    )
    top_figure.update_traces(
        hovertemplate="%{y}<br><b>%{x:,.0f} PLN</b><extra></extra>"
    )
    top_figure.update_layout(xaxis_title=T["axis_sales"], yaxis_title="")
    left.plotly_chart(chart_layout(top_figure, 520), width="stretch")

    country_sales = (
        filtered.groupby("country", as_index=False)["sales_pln"]
        .sum()
        .query("sales_pln > 0")
    )
    country_sales["iso3"] = country_sales["country"].map(ISO2_TO_ISO3)
    country_sales = country_sales.dropna(subset=["iso3"])
    map_figure = px.choropleth(
        country_sales,
        locations="iso3",
        color="sales_pln",
        hover_name="country",
        hover_data={"iso3": False, "sales_pln": ":,.0f"},
        color_continuous_scale=["#DBEAFE", "#60A5FA", "#2563EB", "#0F766E"],
        title=T["map_title"],
        labels={"sales_pln": T["axis_sales"]},
    )
    map_figure.update_geos(
        showframe=False,
        showcoastlines=True,
        coastlinecolor="#CBD5E1",
        showland=True,
        landcolor="#F8FAFC",
        showcountries=True,
        countrycolor="white",
        projection_type="natural earth",
        fitbounds="locations",
    )
    map_figure.update_layout(
        coloraxis_colorbar=dict(title="PLN", thickness=12, len=.65),
        geo=dict(bgcolor="white"),
    )
    right.plotly_chart(chart_layout(map_figure, 520), width="stretch")

with trends_tab:
    controls, charts = st.columns([1, 3])
    controls.info(T["yoy_info"])
    ALL_CUSTOMERS = T["all_customers"]
    comparison_customers = (
        dimension_filtered.groupby("customer")
        .agg(years=("year", "nunique"), sales=("sales_pln", "sum"))
        .query("years >= 2")
        .sort_values("sales", ascending=False)
        .index.tolist()
    )
    if not comparison_customers:
        comparison_customers = sorted(
            dimension_filtered["customer"].dropna().unique()
        )
    comparison_customers = [ALL_CUSTOMERS] + comparison_customers
    available_months = sorted(
        dimension_filtered["month"].dropna().astype(int).unique()
    )
    current_month = int(today.month)
    month_index = (
        available_months.index(current_month)
        if current_month in available_months else len(available_months) - 1
    )
    selected_month = controls.selectbox(
        T["comparison_month"],
        available_months,
        index=month_index,
        format_func=lambda value: f"{value:02d}",
    )
    selected_customer = controls.selectbox(T["customer"], comparison_customers)
    if selected_customer == ALL_CUSTOMERS:
        customer_data = dimension_filtered
    else:
        customer_data = dimension_filtered[
            dimension_filtered["customer"] == selected_customer
        ]
    monthly_yoy = (
        customer_data[customer_data["month"] == selected_month]
        .groupby("year", as_index=False)["sales_pln"]
        .sum()
    )
    ytd_yoy = (
        customer_data[customer_data["month"] <= selected_month]
        .groupby("year", as_index=False)["sales_pln"]
        .sum()
    )
    chart_left, chart_right = charts.columns(2)
    for target, data, title, color in [
        (chart_left, monthly_yoy, T["yoy_monthly_title"], PRIMARY),
        (chart_right, ytd_yoy, T["yoy_ytd_title"], ACCENT),
    ]:
        figure = px.bar(
            data,
            x="year",
            y="sales_pln",
            text_auto=".3s",
            title=title,
            color_discrete_sequence=[color],
        )
        figure.update_layout(xaxis_title=T["axis_year"], yaxis_title=T["axis_sales"])
        figure.update_xaxes(type="category", dtick=1)
        target.plotly_chart(chart_layout(figure), width="stretch")

with details_tab:
    display_columns = [
        "invoice_date", "invoice_number", "customer", "country", "region",
        "currency", "invoice_type", "sales_pln", "sales_gross_pln", "plant",
    ]
    display_columns = [column for column in display_columns if column in filtered.columns]
    table = filtered[display_columns].sort_values("invoice_date", ascending=False)
    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        column_config={
            "invoice_date": st.column_config.DateColumn(T["col_date"], format="DD.MM.YYYY"),
            "sales_pln": st.column_config.NumberColumn(T["col_net"], format="%.2f PLN"),
            "sales_gross_pln": st.column_config.NumberColumn(T["col_gross"], format="%.2f PLN"),
        },
    )
    csv = table.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button(
        T["download_csv"], csv, "sales_dashboard_export.csv", "text/csv",
        width="stretch",
    )

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
            st.warning(T["forecast_no_stl"])

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
