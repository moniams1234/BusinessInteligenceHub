import streamlit as st

st.set_page_config(
    page_title="Business Intelligence Hub",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        /* ── hide Streamlit chrome ── */
        [data-testid="stSidebarNav"]     { display: none; }
        [data-testid="collapsedControl"] { display: none; }
        header[data-testid="stHeader"]   { display: none; }
        footer                           { display: none; }

        /* ── dark radial background ── */
        .stApp {
            background: radial-gradient(ellipse at 20% 20%, #1a2f5a 0%, #0F172A 55%, #091120 100%);
            min-height: 100vh;
        }
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }

        /* ── hero ── */
        .hub-hero {
            text-align: center;
            padding: 34px 24px 56px;
        }
        .hub-logo {
            max-width: 1100px;
            margin: 0 auto 12px;
            font-size: 3.4rem;
            line-height: 1.08;
            letter-spacing: 0.02em;
            font-weight: 800;
            background: linear-gradient(90deg, #60A5FA, #34D399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            overflow-wrap: break-word;
        }
        .hub-tagline {
            font-size: 1.05rem;
            color: #8FB0E6;
            letter-spacing: 0.06em;
            margin: 0;
        }
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label { color: #8FB0E6 !important; }

        /* ── grid wrapper ── */
        .hub-grid {
            max-width: 880px;
            margin: 0 auto;
            padding: 0 32px 80px;
        }

        /* ── force button wrappers to fill columns ── */
        [data-testid="stColumn"] > div,
        [data-testid="stColumn"] .element-container,
        [data-testid="stColumn"] [data-testid="stButton"] {
            width: 100% !important;
        }

        /* ── shared tile button styles ── */
        [data-testid="stColumn"] [data-testid="stButton"] > button {
            width: 100% !important;
            min-height: 300px !important;
            border-radius: 22px !important;
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            background: rgba(255, 255, 255, 0.045) !important;
            white-space: pre-line !important;
            text-align: center !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 6px !important;
            padding: 40px 32px !important;
            font-family: inherit !important;
            line-height: 1.5 !important;
            backdrop-filter: blur(14px) !important;
            -webkit-backdrop-filter: blur(14px) !important;
            transition: transform 0.32s cubic-bezier(.22,.68,0,1.2),
                        box-shadow 0.32s ease,
                        border-color 0.32s ease,
                        background 0.32s ease !important;
            overflow: hidden !important;
            font-size: 0.95rem !important;
        }

        /* ── Sales tile ── */
        [data-testid="stColumn"]:first-of-type [data-testid="stButton"] > button {
            border-top: 3px solid #2563EB !important;
            color: #EAF1FF !important;
            box-shadow: 0 4px 30px rgba(37, 99, 235, 0.12) !important;
        }
        [data-testid="stColumn"]:first-of-type [data-testid="stButton"] > button:hover {
            transform: translateY(-10px) scale(1.01) !important;
            background: rgba(37, 99, 235, 0.10) !important;
            border-color: rgba(37, 99, 235, 0.45) !important;
            box-shadow:
                0 30px 65px rgba(37, 99, 235, 0.28),
                0 10px 25px rgba(0, 0, 0, 0.45) !important;
        }

        /* ── Stock tile ── */
        [data-testid="stColumn"]:last-of-type [data-testid="stButton"] > button {
            border-top: 3px solid #0EA5A4 !important;
            color: #EAF1FF !important;
            box-shadow: 0 4px 30px rgba(14, 165, 164, 0.12) !important;
        }
        [data-testid="stColumn"]:last-of-type [data-testid="stButton"] > button:hover {
            transform: translateY(-10px) scale(1.01) !important;
            background: rgba(14, 165, 164, 0.10) !important;
            border-color: rgba(14, 165, 164, 0.45) !important;
            box-shadow:
                0 30px 65px rgba(14, 165, 164, 0.28),
                0 10px 25px rgba(0, 0, 0, 0.45) !important;
        }

        /* ── footer ── */
        .hub-footer {
            text-align: center;
            color: rgba(139, 176, 230, 0.35);
            font-size: 0.75rem;
            padding-bottom: 32px;
            letter-spacing: 0.06em;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

TRANSLATIONS = {
    "PL": {
        "choose_app": "Wybierz aplikację",
        "sales_label": "📊\n\nSales\n\nDashboard sprzedażowy\nfaktury · KPI · trendy R/R\n\n▶  Otwórz",
        "stock_label": "📦\n\nOtiocon Stock\n\nWiekowanie zapasów\ni kalkulacja rezerw\n\n▶  Otwórz",
        "footer": "Business Intelligence Hub &nbsp;·&nbsp; 2026",
    },
    "EN": {
        "choose_app": "Choose an application",
        "sales_label": "📊\n\nSales\n\nSales dashboard\ninvoices · KPI · YoY trends\n\n▶  Open",
        "stock_label": "📦\n\nOtiocon Stock\n\nInventory aging\nand reserve calculation\n\n▶  Open",
        "footer": "Business Intelligence Hub &nbsp;·&nbsp; 2026",
    },
}

_, language_col = st.columns([5, 1])
with language_col:
    language = st.radio(
        "Język / Language",
        ["PL", "EN"],
        horizontal=True,
        key="hub_language",
    )
text = TRANSLATIONS[language]

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hub-hero">
        <div class="hub-logo">Business Intelligence Hub</div>
        <p class="hub-tagline">{text["choose_app"]}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Cards ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="hub-grid">', unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

SALES_LABEL = text["sales_label"]
STOCK_LABEL = text["stock_label"]

with col1:
    if st.button(SALES_LABEL, key="go_sales"):
        st.switch_page("pages/Sales.py")

with col2:
    if st.button(STOCK_LABEL, key="go_stock"):
        st.switch_page("pages/Otiocon_Stock.py")

st.markdown("</div>", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="hub-footer">{text["footer"]}</div>',
    unsafe_allow_html=True,
)
