import io
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_refresh_stock import (
    get_stock_refresh_status,
    run_refresh_stock,
    start_daily_refresh_stock,
)
from auth import get_session_user, init_db

init_db()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "stock_dashboard.db"
MAPPING_PATH = BASE_DIR / "data" / "default_mapping.xlsx"
TABLE_NAME = "stock_data"

BUCKET_ORDER = [
    "0-3 mcy",
    "3-6 mcy",
    "6-9 mcy",
    "9-12 mcy",
    "pow 12 mcy",
    "data > dzień analizy",
    "błąd daty",
]
PALETTE = ["#22C55E", "#2563EB", "#F59E0B", "#EF4444", "#8B5CF6", "#6B7280"]

st.set_page_config(
    page_title="Otiocon Stock",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _auth_guard() -> tuple[str, dict]:
    tok = st.query_params.get("token") or st.session_state.get("token", "")
    if tok:
        st.session_state["token"] = tok
    current_user = get_session_user(tok) if tok else None
    if current_user is None:
        st.error("Brak autoryzacji. Zaloguj się w Business Intelligence Hub.")
        st.link_button("Wróć do Hub", url="/")
        st.stop()
    if "stock" not in current_user["permissions"]:
        st.error("Nie masz dostępu do aplikacji Otiocon Stock. Skontaktuj się z administratorem.")
        st.link_button("Wróć do Hub", url=f"/?token={tok}")
        st.stop()
    return tok, current_user


_auth_token, _auth_user = _auth_guard()

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
        padding: 18px 20px;
        text-align: center;
        margin-bottom: 8px;
    }
    .kpi-label { font-size: 0.75rem; color: #8FB0E6; letter-spacing: 0.08em;
                 text-transform: uppercase; margin-bottom: 6px; }
    .kpi-value { font-size: 1.55rem; font-weight: 800; color: #EAF1FF; }
    .kpi-split-value { font-size: 1.28rem; font-weight: 800; color: #EAF1FF; line-height: 1.35; }
    .kpi-sub   { font-size: 0.78rem; color: #5580B5; margin-top: 4px; }
    .stButton > button {
        border: 0 !important;
        border-radius: 11px !important;
        background: linear-gradient(135deg, #2563EB, #0EA5A4) !important;
        color: white !important;
        font-weight: 700 !important;
        box-shadow: 0 8px 20px rgba(37, 99, 235, .22) !important;
        transition: transform .18s ease, box-shadow .18s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 12px 26px rgba(37, 99, 235, .30) !important;
    }
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label,
    .stRadio label, .stRadio [data-baseweb="radio"] > div,
    .stDateInput label, .stSelectbox label,
    .stFileUploader label,
    [data-testid="stCaptionContainer"] p { color: #8FB0E6 !important; }
    .stRadio [data-baseweb="radio"] span { color: #EAF1FF !important; }
    [data-baseweb="tab"] p,
    [data-baseweb="tab"] button p,
    button[role="tab"] p { color: #C8DCFF !important; }
    [data-baseweb="tab"][aria-selected="true"] p,
    [data-baseweb="tab"][aria-selected="true"] button p,
    button[role="tab"][aria-selected="true"] p { color: #EAF1FF !important; }
    .stSelectbox [data-baseweb="select"],
    .stSelectbox [data-baseweb="select"] * { cursor: pointer !important; }

    /* ── pointer cursor on all interactive elements ── */
    button, a, summary,
    [role="button"], [role="tab"], [role="option"], [role="radio"], [role="checkbox"],
    .stButton > button,
    [data-testid="stFormSubmitButton"] > button,
    [data-testid="stLinkButton"] a,
    [data-testid="stDownloadButton"] > button,
    [data-baseweb="tab"],
    [data-baseweb="radio"] label,
    [data-baseweb="checkbox"] label,
    [data-testid="stRadio"] label,
    [data-testid="stCheckbox"] label,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] details summary,
    [data-testid="stSelectbox"] div[data-baseweb="select"],
    [data-testid="stDateInput"] input,
    select, option {
        cursor: pointer !important;
    }
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextArea"] textarea {
        cursor: text !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Background refresh (once per session) ──────────────────────────────────
if "stock_refresh_started" not in st.session_state:
    start_daily_refresh_stock()
    st.session_state["stock_refresh_started"] = True

# ── Analysis date ──────────────────────────────────────────────────────────
analysis_date = st.date_input("📅 Data analizy", value=date.today())

# ── Status bar ─────────────────────────────────────────────────────────────
status = get_stock_refresh_status()
state = status.get("state", "")
hdr_l, hdr_refresh, hdr_back = st.columns([6, 1, 1])
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
with hdr_refresh:
    if st.button("↻ Odśwież dane", key="refresh_stock_selected_date"):
        with st.spinner(f"Synchronizacja z MyPrint dla daty {analysis_date}…"):
            run_refresh_stock(force=True, analysis_date=analysis_date)
        st.rerun()
with hdr_back:
    if st.button("← Main menu", key="top_main_menu"):
        st.switch_page("app.py")

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
        if uploaded_mapping is None:
            st.info("Nie wgrano własnego mappingu — używam data/default_mapping.xlsx.")
        active_mapping_path = uploaded_mapping or MAPPING_PATH  # type: ignore[assignment]

# ── Load data ──────────────────────────────────────────────────────────────
def _load_stock_for_date(selected_date: date) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        columns = [
            row[1]
            for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()
        ]
        if "analysis_date" not in columns:
            return pd.DataFrame()
        return pd.read_sql(
            f"SELECT * FROM {TABLE_NAME} WHERE analysis_date = ?",
            conn,
            params=(selected_date.isoformat(),),
        )


df = _load_stock_for_date(analysis_date)

if df.empty:
    with st.spinner(f"Brak danych w bazie dla {analysis_date}. Pobieram z MyPrint…"):
        refresh_result = run_refresh_stock(force=True, analysis_date=analysis_date)
    for _ in range(6):
        df = _load_stock_for_date(analysis_date)
        if not df.empty:
            break
        time.sleep(0.5)
    if not df.empty or (
        refresh_result.get("state") == "success"
        and refresh_result.get("analysis_date") == analysis_date.isoformat()
    ):
        st.rerun()

if df.empty:
    status_after_load = get_stock_refresh_status()
    load_error = status_after_load.get("error")
    if not load_error:
        load_error = (
            f"Brak rekordów w bazie dla daty {analysis_date.isoformat()} "
            "po próbie synchronizacji."
        )
    st.error(
        "Nie udało się załadować danych stock dla wybranej daty. "
        f"{load_error}"
    )
    if st.button("← Main menu", key="error_main_menu"):
        st.switch_page("app.py")
    st.stop()

if df.empty:
    st.warning("Baza danych jest pusta.")
    st.stop()

df["receipt_date"] = pd.to_datetime(df["receipt_date"], errors="coerce")
df["stock_value"]  = pd.to_numeric(df["stock_value"], errors="coerce").fillna(0.0)

# Always apply the active mapping. If the user did not upload a file, use defaults.
from import_stock import apply_mapping, assign_status, calculate_aging, calculate_reserves, load_mapping

m1, m2 = load_mapping(active_mapping_path)
df = apply_mapping(df, m1, m2)
df = calculate_aging(df, analysis_date)
df = calculate_reserves(df)
df = assign_status(df)

# ── KPI cards ──────────────────────────────────────────────────────────────
total_value   = df["stock_value"].sum()
total_reserve = df["reserve_amount"].sum()
pct_reserve   = (total_reserve / total_value * 100) if total_value > 0 else 0.0
n_items       = len(df)

by_index = (
    df.groupby("rodzaj_indeksu")[["stock_value", "reserve_amount"]].sum()
    if "rodzaj_indeksu" in df.columns
    else pd.DataFrame(columns=["stock_value", "reserve_amount"])
)


def _index_value(index_type: str, column: str) -> float:
    if index_type not in by_index.index:
        return 0.0
    return float(by_index.loc[index_type, column])


prowax_value = _index_value("PROWAX", "stock_value")
non_prowax_value = _index_value("NON PROWAX", "stock_value")
prowax_reserve = _index_value("PROWAX", "reserve_amount")
non_prowax_reserve = _index_value("NON PROWAX", "reserve_amount")
prowax_pct = (prowax_reserve / prowax_value * 100) if prowax_value > 0 else 0.0
non_prowax_pct = (
    (non_prowax_reserve / non_prowax_value * 100)
    if non_prowax_value > 0
    else 0.0
)

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

k5, k6, k7 = st.columns(3)
for col, label, prowax_val, non_prowax_val, sub in [
    (
        k5,
        "Wartość magazynu",
        f"{prowax_value:,.0f} PLN",
        f"{non_prowax_value:,.0f} PLN",
        "",
    ),
    (
        k6,
        "Kwota rezerwy",
        f"{prowax_reserve:,.0f} PLN",
        f"{non_prowax_reserve:,.0f} PLN",
        "",
    ),
    (
        k7,
        "% rezerwy",
        f"{prowax_pct:.1f}%",
        f"{non_prowax_pct:.1f}%",
        "rezerwa / wartość",
    ),
]:
    col.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-split-value">PROWAX: {prowax_val}</div>'
        f'<div class="kpi-split-value">NON PROWAX: {non_prowax_val}</div>'
        f'<div class="kpi-sub">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

_chart_bg = {"paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)",
             "font_color": "#EAF1FF", "title_font_color": "#EAF1FF",
             "legend_font_color": "#8FB0E6"}

# ── Wykres 1 + 2 ───────────────────────────────────────────────────────────
col_c1, col_c2 = st.columns(2)

with col_c1:
    if "rodzaj_indeksu" in df.columns:
        pie_df = df.groupby("rodzaj_indeksu")["stock_value"].sum().reset_index()
        fig = px.pie(pie_df, names="rodzaj_indeksu", values="stock_value",
                     hole=0.55,
                     title="Udział procentowy stanu magazynowego: PROWAX / NON PROWAX")
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(**_chart_bg, height=420, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig, use_container_width=True)

with col_c2:
    if "rodzaj_indeksu" in df.columns:
        compare_df = (df.groupby("rodzaj_indeksu")[["stock_value", "reserve_amount"]]
                      .sum().reset_index())
        compare_long = compare_df.melt(
            id_vars="rodzaj_indeksu",
            value_vars=["stock_value", "reserve_amount"],
            var_name="Miara", value_name="Wartość",
        )
        compare_long["Miara"] = compare_long["Miara"].map(
            {"stock_value": "Wartość mag.", "reserve_amount": "Kwota rezerwy"}
        )
        fig = px.bar(compare_long, x="Wartość", y="rodzaj_indeksu", color="Miara",
                     barmode="group", orientation="h",
                     title="PROWAX / NON PROWAX – stan magazynu i rezerwa",
                     text_auto=".2s",
                     labels={"rodzaj_indeksu": "", "Wartość": "Wartość [PLN]"})
        fig.update_layout(**_chart_bg, height=420, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig, use_container_width=True)

# ── Wykres 3 + 4 ───────────────────────────────────────────────────────────
col_c3, col_c4 = st.columns(2)

with col_c3:
    if "type_of_materials" in df.columns:
        res_df = (df.groupby("type_of_materials")["reserve_amount"]
                  .sum().reset_index()
                  .sort_values("reserve_amount", ascending=False))
        fig = px.bar(res_df, x="type_of_materials", y="reserve_amount",
                     title="Kwota rezerwy wg Type of materials",
                     text_auto=".2s",
                     labels={"reserve_amount": "Kwota rezerwy [PLN]",
                             "type_of_materials": "Type of materials"})
        fig.update_layout(**_chart_bg, height=420, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig, use_container_width=True)

with col_c4:
    if "aging_bucket" in df.columns and "rodzaj_indeksu" in df.columns:
        aging_df = (df.groupby(["aging_bucket", "rodzaj_indeksu"])["stock_value"]
                    .sum().reset_index())
        aging_df["aging_bucket"] = pd.Categorical(
            aging_df["aging_bucket"], categories=BUCKET_ORDER, ordered=True
        )
        aging_df = aging_df.sort_values("aging_bucket")
        fig = px.bar(aging_df, x="aging_bucket", y="stock_value", color="rodzaj_indeksu",
                     barmode="stack",
                     title="Struktura wieku zapasu wg przedziałów",
                     text_auto=".2s",
                     labels={"stock_value": "Wartość magazynowa [PLN]",
                             "aging_bucket": "Przedział wiekowania",
                             "rodzaj_indeksu": "Rodzaj indeksu"})
        fig.update_layout(**_chart_bg, height=420, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig, use_container_width=True)

# ── Wykres 5 ───────────────────────────────────────────────────────────────
if "warehouse" in df.columns:
    top_mag = (df.groupby("warehouse")["reserve_amount"]
               .sum().reset_index()
               .sort_values("reserve_amount", ascending=False)
               .head(10))
    fig = px.bar(top_mag.sort_values("reserve_amount", ascending=True),
                 x="reserve_amount", y="warehouse", orientation="h",
                 title="TOP 10 magazynów wg kwoty rezerwy",
                 text_auto=".2s",
                 labels={"reserve_amount": "Kwota rezerwy [PLN]", "warehouse": ""})
    fig.update_layout(**_chart_bg, height=460, margin=dict(l=20, r=20, t=60, b=20))
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
_EXPORT_COL_ORDER = [
    "material_index", "batch", "barcode", "supplier_code", "warehouse",
    "pz_number", "invoice1", "invoice2", "material_name", "material_type",
    "stock_qty", "unit1", "stock_qty2", "unit2", "stock_qty3", "unit3",
    "stock_value", "currency", "receipt_date", "dkk_rate", "stock_value_dkk",
    "rodzaj_indeksu", "type_of_materials", "aging_bucket",
    "reserve_pct", "status", "reserve_amount",
]
_COL_PL = {
    "material_index": "Index materiałowy",
    "batch": "Partia",
    "barcode": "Kod kreskowy",
    "supplier_code": "Kod dostawcy",
    "warehouse": "Magazyn",
    "pz_number": "Przyjęcie [PZ]",
    "invoice1": "Numer faktury",
    "invoice2": "Numer faktury.1",
    "material_name": "Nazwa materiału",
    "material_type": "Typ surowca",
    "stock_qty": "Stan mag.",
    "unit1": "jm.1",
    "stock_qty2": "Stan mag..1",
    "unit2": "jm.2",
    "stock_qty3": "Stan mag..2",
    "unit3": "jm.3",
    "stock_value": "Wartość mag.",
    "currency": "waluta",
    "receipt_date": "Data przyjęcia",
    "dkk_rate": "Kurs DKK",
    "stock_value_dkk": "Wartość DKK",
    "rodzaj_indeksu": "Rodzaj indeksu",
    "type_of_materials": "Type of materials",
    "aging_bucket": "Przedział wiekowania",
    "reserve_pct": "% rezerwy",
    "status": "Status pozycji",
    "reserve_amount": "Kwota rezerwy",
}

_XL_ORANGE      = "E8650A"
_XL_LIGHT_ORANGE = "FAD7B8"
_XL_DARK_GREY   = "404040"
_XL_LIGHT_GREY  = "F2F2F2"
_XL_WHITE       = "FFFFFF"


def _build_excel(detail_df: pd.DataFrame, analysis_date_val, mapping_label: str = "domyślny") -> bytes:
    buf = io.BytesIO()
    date_str = (analysis_date_val.strftime("%d.%m.%Y")
                if hasattr(analysis_date_val, "strftime") else str(analysis_date_val))

    # ── Dane szczegółowe — rename columns to Polish ────────────────────────
    export_cols = [c for c in _EXPORT_COL_ORDER if c in detail_df.columns]
    df_exp = detail_df[export_cols].rename(columns=_COL_PL)

    # ── Podsumowanie — pivot: index=Magazyn, cols=[type,rodzaj,status] ─────
    piv_dims = [c for c in ["type_of_materials", "rodzaj_indeksu", "status"]
                if c in detail_df.columns]
    if piv_dims and "warehouse" in detail_df.columns:
        piv = detail_df.pivot_table(
            values=["reserve_amount", "stock_value"],
            index="warehouse",
            columns=piv_dims,
            aggfunc="sum",
            fill_value=0,
        )
        piv = piv.rename(
            columns={"reserve_amount": "Kwota rezerwy", "stock_value": "Wartość mag."},
            level=0,
        )
        piv.index.name = "Magazyn"
        summary_flat = piv.copy()
        summary_flat.columns = [" | ".join(str(c) for c in col) for col in summary_flat.columns]
        summary_flat = summary_flat.reset_index()
        total_row = {"Magazyn": "SUMA KOŃCOWA",
                     **{c: summary_flat[c].sum() for c in summary_flat.columns[1:]}}
        summary_flat = pd.concat([summary_flat, pd.DataFrame([total_row])], ignore_index=True)
    else:
        summary_flat = pd.DataFrame()

    # ── Statistics for Metryki ogólne ─────────────────────────────────────
    n_total    = len(detail_df)
    n_unmapped = int((detail_df.get("type_of_materials", pd.Series(dtype=str)) == "UNMAPPED").sum())
    n_mapped   = n_total - n_unmapped
    n_date_err = int((detail_df.get("aging_bucket", pd.Series(dtype=str)) == "błąd daty").sum())
    n_reserve  = int((detail_df.get("reserve_amount", pd.Series(dtype=float)) > 0).sum())
    tot_reserve = float(detail_df["reserve_amount"].sum()) if "reserve_amount" in detail_df.columns else 0.0
    tot_value   = float(detail_df["stock_value"].sum())   if "stock_value"   in detail_df.columns else 0.0

    warnings_list: list[str] = []
    if n_unmapped > 0:
        warnings_list.append(
            f"⚠️ Liczba rekordów bez przypisanego 'Type of materials' (UNMAPPED): "
            f"{n_unmapped} z {n_total}"
        )

    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        wb = writer.book

        fmt_title    = wb.add_format({"bold": True, "font_size": 13,
                                       "font_color": "#" + _XL_ORANGE, "valign": "vcenter"})
        fmt_header   = wb.add_format({"bold": True, "font_color": "#" + _XL_WHITE,
                                       "bg_color": "#" + _XL_ORANGE, "border": 1,
                                       "align": "center", "valign": "vcenter", "text_wrap": True})
        fmt_pct      = wb.add_format({"num_format": "0%", "border": 1})
        fmt_num      = wb.add_format({"num_format": "#,##0.00", "border": 1})
        fmt_text     = wb.add_format({"border": 1})
        fmt_alt      = wb.add_format({"bg_color": "#" + _XL_LIGHT_GREY, "border": 1})
        fmt_pct_alt  = wb.add_format({"num_format": "0%",       "bg_color": "#" + _XL_LIGHT_GREY, "border": 1})
        fmt_num_alt  = wb.add_format({"num_format": "#,##0.00", "bg_color": "#" + _XL_LIGHT_GREY, "border": 1})
        fmt_total    = wb.add_format({"bold": True, "bg_color": "#" + _XL_LIGHT_ORANGE,
                                       "num_format": "#,##0.00", "border": 1})
        fmt_total_txt = wb.add_format({"bold": True, "bg_color": "#" + _XL_LIGHT_ORANGE, "border": 1})
        fmt_met_hdr  = wb.add_format({"bold": True, "font_color": "#" + _XL_WHITE,
                                       "bg_color": "#" + _XL_DARK_GREY, "border": 1, "align": "center"})
        fmt_met_val  = wb.add_format({"num_format": "#,##0.00", "border": 1,
                                       "bg_color": "#" + _XL_LIGHT_GREY})
        fmt_warn     = wb.add_format({"font_color": "CC6600", "border": 1})
        fmt_ok       = wb.add_format({"font_color": "006600", "border": 1})

        pct_cols_pl = {"% rezerwy"}
        num_cols_pl = {"Wartość mag.", "Kwota rezerwy", "Kurs DKK", "Wartość DKK", "Stan mag."}
        col_widths_pl = {
            "Index materiałowy": 18, "Magazyn": 22, "Typ surowca": 22,
            "Data przyjęcia": 14,   "Wartość mag.": 14, "Rodzaj indeksu": 15,
            "Type of materials": 16, "Przedział wiekowania": 16,
            "% rezerwy": 11,        "Status pozycji": 13, "Kwota rezerwy": 14,
            "Nazwa materiału": 30,
        }

        # ── Arkusz 1: Dane szczegółowe ─────────────────────────────────────
        ws_det = wb.add_worksheet("Dane szczegółowe")
        writer.sheets["Dane szczegółowe"] = ws_det

        ws_det.write(
            0, 0,
            f"Wiekowanie zapasów – dane szczegółowe | "
            f"Data analizy: {date_str} | Mapping: {mapping_label}",
            fmt_title,
        )
        ncols = len(df_exp.columns)
        for ci, col_name in enumerate(df_exp.columns):
            ws_det.write(1, ci, col_name, fmt_header)
        ws_det.set_row(1, 30)

        for ri, row_data in enumerate(df_exp.itertuples(index=False), start=2):
            is_alt = ri % 2 == 0
            for ci, col_name in enumerate(df_exp.columns):
                val = row_data[ci]
                if val is pd.NaT or (isinstance(val, float) and pd.isna(val)):
                    val = ""
                if col_name in pct_cols_pl:
                    fmt = fmt_pct_alt if is_alt else fmt_pct
                elif col_name in num_cols_pl:
                    fmt = fmt_num_alt if is_alt else fmt_num
                else:
                    fmt = fmt_alt if is_alt else fmt_text
                ws_det.write(ri, ci, val, fmt)

        for ci, col_name in enumerate(df_exp.columns):
            ws_det.set_column(ci, ci, col_widths_pl.get(col_name, max(len(str(col_name)) + 2, 10)))

        ws_det.freeze_panes(2, 0)
        ws_det.autofilter(1, 0, 1 + len(df_exp), ncols - 1)

        # ── Arkusz 2: Podsumowanie ─────────────────────────────────────────
        ws_sum = wb.add_worksheet("Podsumowanie")
        writer.sheets["Podsumowanie"] = ws_sum

        ws_sum.write(0, 0, f"Tabela podsumowująca rezerw | Data analizy: {date_str}", fmt_title)

        metrics_start = 4
        if not summary_flat.empty:
            hdr_row = 2
            for ci, col_name in enumerate(summary_flat.columns):
                ws_sum.write(hdr_row, ci, col_name, fmt_header)
            ws_sum.set_row(hdr_row, 40)

            for ri, row_data in enumerate(summary_flat.itertuples(index=False), start=hdr_row + 1):
                is_total = str(row_data[0]) == "SUMA KOŃCOWA"
                for ci, val in enumerate(row_data):
                    if val is pd.NaT or (isinstance(val, float) and pd.isna(val)):
                        val = 0
                    if is_total:
                        f = fmt_total_txt if ci == 0 else fmt_total
                    elif isinstance(val, (int, float)) and not isinstance(val, bool):
                        f = fmt_num_alt if ri % 2 == 0 else fmt_num
                    else:
                        f = fmt_alt if ri % 2 == 0 else fmt_text
                    ws_sum.write(ri, ci, val, f)

            ws_sum.set_column(0, 0, 28)
            for ci in range(1, len(summary_flat.columns)):
                ws_sum.set_column(ci, ci, 20)
            ws_sum.freeze_panes(hdr_row + 1, 1)
            ws_sum.autofilter(hdr_row, 0, hdr_row + len(summary_flat), len(summary_flat.columns) - 1)
            metrics_start = hdr_row + len(summary_flat) + 4

        ws_sum.write(metrics_start,     0, "Metryki ogólne", fmt_met_hdr)
        ws_sum.write(metrics_start,     1, "Wartość",        fmt_met_hdr)
        for i, (label, value) in enumerate([
            ("Łączna liczba rekordów",          n_total),
            ("Zmapowane (Mapp2)",               n_mapped),
            ("Niezmapowane (UNMAPPED)",          n_unmapped),
            ("Błędne daty",                     n_date_err),
            ("Rekordy z rezerwą > 0",           n_reserve),
            ("Łączna kwota rezerwy (PLN)",      tot_reserve),
            ("Łączna wartość magazynowa (PLN)", tot_value),
        ], start=metrics_start + 1):
            ws_sum.write(i, 0, label, fmt_text)
            ws_sum.write(i, 1, value, fmt_met_val)

        # ── Arkusz 3: Log walidacji ────────────────────────────────────────
        ws_log = wb.add_worksheet("Log walidacji")
        writer.sheets["Log walidacji"] = ws_log

        ws_log.write(0, 0, "Log walidacji i ostrzeżeń", fmt_title)
        ws_log.write(1, 0, "Typ",  fmt_header)
        ws_log.write(1, 1, "Opis", fmt_header)
        ws_log.set_column(0, 0, 15)
        ws_log.set_column(1, 1, 80)

        log_row = 2
        for w_msg in warnings_list:
            ws_log.write(log_row, 0, "OSTRZEŻENIE", fmt_warn)
            ws_log.write(log_row, 1, w_msg, fmt_warn)
            log_row += 1
        if log_row == 2:
            ws_log.write(log_row, 0, "OK", fmt_ok)
            ws_log.write(log_row, 1, "Brak błędów i ostrzeżeń.", fmt_ok)

    buf.seek(0)
    return buf.read()


mapping_label = "domyślny" if mapping_source == "Domyślny" else "własny"
exp_col, back_col = st.columns([5, 2])
with exp_col:
    try:
        excel_bytes = _build_excel(df, analysis_date, mapping_label)
        filename_date = analysis_date.strftime("%Y%m%d")
        st.download_button(
            "↓ Pobierz Excel (pełny)",
            data=excel_bytes,
            file_name=f"wiekowanie_zapasow_{filename_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Plik Excel z arkuszami: Dane szczegółowe, Podsumowanie, Log walidacji.",
        )
    except Exception as e:
        st.error(f"Błąd generowania Excel: {e}")
with back_col:
    if st.button("← Main menu", key="bottom_main_menu", use_container_width=True):
        st.switch_page("app.py")
