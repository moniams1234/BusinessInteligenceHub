import streamlit as st

from auth import (
    APP_LABELS,
    authenticate,
    change_password,
    create_session,
    delete_session,
    get_session_user,
    init_db,
    purge_expired_sessions,
)

st.set_page_config(
    page_title="Business Intelligence Hub",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()
purge_expired_sessions()

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
            padding: 24px 32px !important;
            max-width: 100% !important;
        }

        /* ── hero ── */
        .hub-hero {
            text-align: center;
            padding: 34px 24px 40px;
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
        .hub-owner {
            font-size: 0.8rem;
            color: rgba(143, 176, 230, 0.6);
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin: 10px 0 0;
        }
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label { color: #8FB0E6 !important; }

        /* ── grid wrapper ── */
        .hub-grid {
            max-width: 1000px;
            margin: 0 auto;
            padding: 0 32px 40px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
        }

        /* ── tile as anchor ── */
        .hub-tile {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 8px;
            text-align: center;
            padding: 22px 18px;
            min-height: 180px;
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.10);
            background: rgba(255, 255, 255, 0.045);
            color: #EAF1FF !important;
            text-decoration: none !important;
            font-family: inherit;
            cursor: pointer;
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            transition: transform 0.32s cubic-bezier(.22,.68,0,1.2),
                        box-shadow 0.32s ease,
                        border-color 0.32s ease,
                        background 0.32s ease;
        }
        .hub-tile:hover {
            transform: translateY(-6px) scale(1.01);
            box-shadow:
                0 20px 45px rgba(0, 0, 0, 0.4),
                0 6px 18px rgba(0, 0, 0, 0.45);
        }
        .tile-icon  { font-size: 2rem; line-height: 1; }
        .tile-title { font-size: 1.05rem; font-weight: 700; letter-spacing: 0.01em; }
        .tile-desc  { font-size: 0.8rem; color: rgba(234, 241, 255, 0.7); line-height: 1.4; max-width: 220px; }
        .tile-cta   { font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.85; margin-top: 4px; }
        .hub-tile--sales      { border-top: 3px solid #2563EB; box-shadow: 0 4px 30px rgba(37, 99, 235, 0.12); }
        .hub-tile--sales:hover{ background: rgba(37, 99, 235, 0.10); border-color: rgba(37, 99, 235, 0.45); box-shadow: 0 30px 65px rgba(37, 99, 235, 0.28); }
        .hub-tile--stock      { border-top: 3px solid #0EA5A4; box-shadow: 0 4px 30px rgba(14, 165, 164, 0.12); }
        .hub-tile--stock:hover{ background: rgba(14, 165, 164, 0.10); border-color: rgba(14, 165, 164, 0.45); box-shadow: 0 30px 65px rgba(14, 165, 164, 0.28); }
        .hub-tile--admin      { border-top: 3px solid #F59E0B; box-shadow: 0 4px 30px rgba(245, 158, 11, 0.12); }
        .hub-tile--admin:hover{ background: rgba(245, 158, 11, 0.10); border-color: rgba(245, 158, 11, 0.45); box-shadow: 0 30px 65px rgba(245, 158, 11, 0.28); }

        /* ── coming-soon CFO tiles ── */
        .hub-tile--soon {
            cursor: default;
            opacity: 0.55;
            border-style: dashed;
        }
        .hub-tile--soon:hover {
            transform: none;
            box-shadow: none;
        }
        .hub-tile--budget      { border-top: 3px solid #A78BFA; }
        .hub-tile--investment  { border-top: 3px solid #F472B6; }
        .hub-tile--cashflow    { border-top: 3px solid #38BDF8; }
        .tile-soon-badge {
            font-size: 0.68rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: rgba(234, 241, 255, 0.55);
            border: 1px solid rgba(234, 241, 255, 0.25);
            border-radius: 999px;
            padding: 2px 10px;
            margin-top: 2px;
        }

        /* ── login form ── */
        .hub-login-title {
            color: #EAF1FF !important;
            font-size: 1.4rem !important;
            font-weight: 600 !important;
            margin: 0 0 18px 0 !important;
            text-align: center;
            letter-spacing: 0.02em;
        }
        [data-testid="stForm"] {
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            border-radius: 22px !important;
            background: rgba(255, 255, 255, 0.045) !important;
            padding: 32px !important;
            backdrop-filter: blur(14px) !important;
            -webkit-backdrop-filter: blur(14px) !important;
        }
        [data-testid="stForm"] label,
        [data-testid="stForm"] label p {
            color: #8FB0E6 !important;
            font-size: 0.9rem !important;
        }
        /* nuke all nested white backgrounds inside form inputs */
        [data-testid="stForm"] [data-testid="stTextInput"],
        [data-testid="stForm"] [data-testid="stTextInput"] > div,
        [data-testid="stForm"] [data-testid="stTextInput"] > div > div,
        [data-testid="stForm"] [data-testid="stTextInput"] > div > div > div,
        [data-testid="stForm"] [data-baseweb="input"] > div,
        [data-testid="stForm"] [data-baseweb="base-input"] > div {
            background: transparent !important;
            background-color: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
        }
        [data-testid="stForm"] [data-baseweb="input"],
        [data-testid="stForm"] [data-baseweb="base-input"] {
            background: rgba(255,255,255,0.14) !important;
            background-color: rgba(255,255,255,0.14) !important;
            border: 1.5px solid rgba(143,176,230,0.55) !important;
            border-radius: 12px !important;
            overflow: hidden;
        }
        [data-testid="stForm"] [data-baseweb="input"]:focus-within,
        [data-testid="stForm"] [data-baseweb="base-input"]:focus-within {
            border-color: #60A5FA !important;
            background: rgba(255,255,255,0.18) !important;
            background-color: rgba(255,255,255,0.18) !important;
            box-shadow: 0 0 0 3px rgba(96,165,250,0.25) !important;
        }
        [data-testid="stForm"] input {
            background: transparent !important;
            background-color: transparent !important;
            color: #EAF1FF !important;
            -webkit-text-fill-color: #EAF1FF !important;
            border: 0 !important;
            font-size: 1rem !important;
            caret-color: #60A5FA !important;
        }
        [data-testid="stForm"] input[type="password"] {
            letter-spacing: 0.2em !important;
            font-family: 'Courier New', monospace !important;
            font-size: 1.05rem !important;
        }
        [data-testid="stForm"] input::placeholder {
            color: rgba(143,176,230,0.55) !important;
            letter-spacing: normal !important;
            font-family: inherit !important;
        }
        [data-testid="stForm"] input:-webkit-autofill {
            -webkit-box-shadow: 0 0 0 30px rgba(15,23,42,0.9) inset !important;
            -webkit-text-fill-color: #EAF1FF !important;
            caret-color: #60A5FA !important;
        }
        [data-testid="stForm"] button svg { fill: #8FB0E6 !important; }
        .hub-user-bar {
            text-align: right;
            color: #8FB0E6;
            font-size: 0.85rem;
            padding: 12px 32px 12px;
        }
        .hub-user-bar strong { color: #EAF1FF; }

        /* ── footer ── */
        .hub-footer {
            text-align: center;
            color: rgba(139, 176, 230, 0.35);
            font-size: 0.75rem;
            padding-bottom: 32px;
            letter-spacing: 0.06em;
        }

        /* ── fancy buttons (submit + regular) ── */
        .stButton > button,
        [data-testid="stFormSubmitButton"] > button,
        [data-testid="baseButton-secondary"],
        [data-testid="baseButton-primary"],
        button[kind="secondary"],
        button[kind="primary"],
        button[kind="secondaryFormSubmit"],
        button[kind="primaryFormSubmit"] {
            background: linear-gradient(135deg, #2563EB, #0EA5A4) !important;
            background-color: #2563EB !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(96,165,250,0.35) !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            padding: 10px 20px !important;
            letter-spacing: 0.02em !important;
            box-shadow: 0 6px 18px rgba(37,99,235,0.28) !important;
            transition: transform 0.2s, box-shadow 0.2s, filter 0.2s !important;
        }
        .stButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover,
        button[kind="secondary"]:hover,
        button[kind="primary"]:hover,
        button[kind="secondaryFormSubmit"]:hover,
        button[kind="primaryFormSubmit"]:hover {
            transform: translateY(-2px);
            filter: brightness(1.08);
            box-shadow: 0 10px 28px rgba(37,99,235,0.45) !important;
            color: #FFFFFF !important;
        }
        .stButton > button p,
        [data-testid="stFormSubmitButton"] > button p,
        button[kind] p,
        button[kind] div {
            color: #FFFFFF !important;
        }

        /* Wyloguj (main-body outside form) */
        [data-testid="stButton"] > button {
            background: linear-gradient(135deg, #2563EB, #0EA5A4) !important;
            color: #FFFFFF !important;
        }

        /* ── password dots — force high-contrast rendering ── */
        input[type="password"] {
            font-family: 'Courier New', 'Consolas', monospace !important;
            letter-spacing: 0.3em !important;
            font-size: 1.1rem !important;
            color: #EAF1FF !important;
            -webkit-text-fill-color: #EAF1FF !important;
            font-weight: 900 !important;
        }

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
        input[type="password"] { cursor: text !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

def _tile_content(icon: str, title: str, desc: str, cta: str) -> str:
    return (
        f'<span class="tile-icon">{icon}</span>'
        f'<span class="tile-title">{title}</span>'
        f'<span class="tile-desc">{desc}</span>'
        f'<span class="tile-cta">{cta}</span>'
    )


def _tile_content_soon(icon: str, title: str, desc: str, badge: str) -> str:
    return (
        f'<span class="tile-icon">{icon}</span>'
        f'<span class="tile-title">{title}</span>'
        f'<span class="tile-desc">{desc}</span>'
        f'<span class="tile-soon-badge">{badge}</span>'
    )


TRANSLATIONS = {
    "PL": {
        "choose_app": "Wybierz aplikację",
        "login_title": "Logowanie",
        "login_username": "Login",
        "login_password": "Hasło",
        "login_submit": "Zaloguj",
        "login_error": "Nieprawidłowy login lub hasło.",
        "logout": "Wyloguj",
        "logged_in_as": "Zalogowany jako",
        "must_change_title": "Zmień hasło",
        "must_change_info": "Ze względów bezpieczeństwa musisz zmienić hasło przed dalszą pracą.",
        "new_password": "Nowe hasło",
        "confirm_password": "Potwierdź hasło",
        "change_submit": "Zmień hasło",
        "pw_mismatch": "Hasła się nie zgadzają.",
        "pw_too_short": "Hasło musi mieć co najmniej 6 znaków.",
        "pw_changed": "Hasło zostało zmienione.",
        "no_apps": "Nie masz jeszcze dostępu do żadnej aplikacji. Skontaktuj się z administratorem.",
        "sales_content": _tile_content("📊", "Sales", "Dashboard sprzedażowy · KPI · trendy R/R", "▶ Otwórz"),
        "stock_content": _tile_content("📦", "Stock", "Wiekowanie zapasów i kalkulacja rezerw", "▶ Otwórz"),
        "admin_content": _tile_content("⚙️", "Panel administratora", "Użytkownicy · uprawnienia · hasła", "▶ Otwórz"),
        "budget_content": _tile_content_soon("🎯", "Actual vs Budget", "Porównanie wykonania z budżetem", "Wkrótce"),
        "investment_content": _tile_content_soon("💹", "Investment Analyser", "Analiza inwestycji i rentowności", "Wkrótce"),
        "cashflow_content": _tile_content_soon("💧", "Cash Flow", "Prognoza i monitoring przepływów pieniężnych", "Wkrótce"),
        "footer": "Business Intelligence Hub &nbsp;·&nbsp; 2026",
    },
    "EN": {
        "choose_app": "Choose an application",
        "login_title": "Login",
        "login_username": "Username",
        "login_password": "Password",
        "login_submit": "Sign in",
        "login_error": "Invalid username or password.",
        "logout": "Logout",
        "logged_in_as": "Logged in as",
        "must_change_title": "Change password",
        "must_change_info": "For security reasons you must change your password before continuing.",
        "new_password": "New password",
        "confirm_password": "Confirm password",
        "change_submit": "Change password",
        "pw_mismatch": "Passwords do not match.",
        "pw_too_short": "Password must be at least 6 characters.",
        "pw_changed": "Password changed.",
        "no_apps": "You don't have access to any application yet. Contact your administrator.",
        "sales_content": _tile_content("📊", "Sales", "Sales dashboard · KPI · YoY trends", "▶ Open"),
        "stock_content": _tile_content("📦", "Stock", "Inventory aging and reserve calculation", "▶ Open"),
        "admin_content": _tile_content("⚙️", "Admin panel", "Users · permissions · passwords", "▶ Open"),
        "budget_content": _tile_content_soon("🎯", "Actual vs Budget", "Compare actuals against budget", "Coming soon"),
        "investment_content": _tile_content_soon("💹", "Investment Analyser", "Investment and return analysis", "Coming soon"),
        "cashflow_content": _tile_content_soon("💧", "Cash Flow", "Cash flow forecasting and monitoring", "Coming soon"),
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
T = TRANSLATIONS[language]

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hub-hero">
        <div class="hub-logo">Business Intelligence Hub</div>
        <p class="hub-tagline">{T["choose_app"]}</p>
        <p class="hub-owner">Monika Siurnicka-Ślusarczyk</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Session lookup ────────────────────────────────────────────────────────────
def _current_token() -> str:
    tok = st.query_params.get("token")
    if tok:
        st.session_state["token"] = tok
        return tok
    return st.session_state.get("token", "")


token = _current_token()
user = get_session_user(token) if token else None


# ── Not logged in → login form ────────────────────────────────────────────────
if user is None:
    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        with st.form("login_form"):
            st.markdown(
                f'<div class="hub-login-title">{T["login_title"]}</div>',
                unsafe_allow_html=True,
            )
            username_input = st.text_input(
                T["login_username"], key="login_username", placeholder=T["login_username"]
            )
            password_input = st.text_input(
                T["login_password"],
                type="password",
                key="login_password",
                placeholder=T["login_password"],
            )
            submitted = st.form_submit_button(
                T["login_submit"], use_container_width=True
            )
            if submitted:
                authed = authenticate(username_input.strip(), password_input)
                if authed is None:
                    st.error(T["login_error"])
                else:
                    new_token = create_session(authed["username"])
                    st.session_state["token"] = new_token
                    st.query_params["token"] = new_token
                    st.rerun()
    st.markdown(
        f'<div class="hub-footer">{T["footer"]}</div>', unsafe_allow_html=True
    )
    st.stop()


# ── Must change password ──────────────────────────────────────────────────────
if user["must_change_password"]:
    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        with st.form("change_pw_form"):
            st.markdown(
                f'<div class="hub-login-title">{T["must_change_title"]}</div>',
                unsafe_allow_html=True,
            )
            st.info(T["must_change_info"])
            new_pw = st.text_input(T["new_password"], type="password", key="new_pw")
            confirm_pw = st.text_input(
                T["confirm_password"], type="password", key="confirm_pw"
            )
            submitted = st.form_submit_button(
                T["change_submit"], use_container_width=True
            )
            if submitted:
                if len(new_pw) < 6:
                    st.error(T["pw_too_short"])
                elif new_pw != confirm_pw:
                    st.error(T["pw_mismatch"])
                else:
                    change_password(user["username"], new_pw, clear_must_change=True)
                    st.success(T["pw_changed"])
                    st.rerun()
    st.stop()


# ── Logged in: user bar + tiles ──────────────────────────────────────────────
user_col, logout_col = st.columns([6, 1])
with user_col:
    st.markdown(
        f'<div class="hub-user-bar">{T["logged_in_as"]}: <strong>{user["username"]}</strong>'
        f'{" · admin" if user["is_admin"] else ""}</div>',
        unsafe_allow_html=True,
    )
with logout_col:
    if st.button(T["logout"], key="logout_btn"):
        delete_session(token)
        st.session_state.pop("token", None)
        st.query_params.clear()
        st.rerun()


# ── Tiles (only apps user has access to) ─────────────────────────────────────
tiles: list[str] = []

if "sales" in user["permissions"]:
    tiles.append(
        f'<a class="hub-tile hub-tile--sales" href="/Sales?token={token}" target="_blank" rel="noopener">{T["sales_content"]}</a>'
    )
if "stock" in user["permissions"]:
    tiles.append(
        f'<a class="hub-tile hub-tile--stock" href="/Otiocon_Stock?token={token}" target="_blank" rel="noopener">{T["stock_content"]}</a>'
    )
if user["is_admin"]:
    tiles.append(
        f'<a class="hub-tile hub-tile--admin" href="/Admin?token={token}" target="_blank" rel="noopener">{T["admin_content"]}</a>'
    )
    tiles.append(
        f'<div class="hub-tile hub-tile--soon hub-tile--budget">{T["budget_content"]}</div>'
    )
    tiles.append(
        f'<div class="hub-tile hub-tile--soon hub-tile--investment">{T["investment_content"]}</div>'
    )
    tiles.append(
        f'<div class="hub-tile hub-tile--soon hub-tile--cashflow">{T["cashflow_content"]}</div>'
    )

if not tiles:
    st.warning(T["no_apps"])
else:
    st.markdown(
        '<div class="hub-grid">' + "".join(tiles) + "</div>",
        unsafe_allow_html=True,
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="hub-footer">{T["footer"]}</div>',
    unsafe_allow_html=True,
)
