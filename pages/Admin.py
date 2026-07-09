import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth import (
    APP_LABELS,
    APPS,
    change_password,
    count_admins,
    create_user,
    delete_user,
    get_session_user,
    init_db,
    list_users,
    set_admin,
    set_permission,
)

init_db()

st.set_page_config(
    page_title="Admin · Business Intelligence Hub",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"]     { display: none; }
        [data-testid="collapsedControl"] { display: none; }
        header[data-testid="stHeader"]   { display: none; }

        .stApp {
            background: radial-gradient(ellipse at 20% 20%, #1a2f5a 0%, #0F172A 55%, #091120 100%);
            min-height: 100vh;
        }
        .block-container {
            padding: 32px 40px !important;
            max-width: 1400px !important;
        }

        /* ── typography ── */
        h1, h2, h3, h4, h5, h6 {
            color: #EAF1FF !important;
            letter-spacing: 0.01em;
        }
        h1 {
            background: linear-gradient(90deg, #60A5FA, #34D399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 800 !important;
        }
        h2, h3 { font-weight: 700 !important; }

        .stMarkdown, .stMarkdown p, .stMarkdown li,
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stMarkdownContainer"] span {
            color: #EAF1FF !important;
        }
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p,
        small, .stCaption {
            color: #8FB0E6 !important;
        }
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label,
        label, label p {
            color: #8FB0E6 !important;
            font-size: 0.85rem !important;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            font-weight: 500 !important;
        }

        /* ── inputs (glass, dark) — nuke ALL nested divs to transparent ── */
        [data-testid="stTextInput"],
        [data-testid="stTextInput"] > div,
        [data-testid="stTextInput"] > div > div,
        [data-testid="stTextInput"] > div > div > div,
        [data-testid="stTextInput"] [data-baseweb="input"],
        [data-testid="stTextInput"] [data-baseweb="base-input"],
        [data-testid="stTextInput"] [data-baseweb="input"] > div,
        [data-testid="stTextInput"] [data-baseweb="base-input"] > div,
        .stTextInput,
        .stTextInput div {
            background: transparent !important;
            background-color: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
        }
        /* now apply glass styling to the actual visible container */
        [data-testid="stTextInput"] [data-baseweb="input"],
        [data-testid="stTextInput"] [data-baseweb="base-input"] {
            background: rgba(255,255,255,0.06) !important;
            background-color: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
            border-radius: 12px !important;
            transition: border-color 0.2s, box-shadow 0.2s, background 0.2s !important;
            overflow: hidden;
        }
        [data-testid="stTextInput"] [data-baseweb="input"]:focus-within,
        [data-testid="stTextInput"] [data-baseweb="base-input"]:focus-within {
            border-color: rgba(96,165,250,0.6) !important;
            background: rgba(255,255,255,0.09) !important;
            background-color: rgba(255,255,255,0.09) !important;
            box-shadow: 0 0 0 3px rgba(96,165,250,0.15) !important;
        }
        [data-testid="stTextInput"] input,
        [data-baseweb="input"] input,
        [data-baseweb="base-input"] input {
            background: transparent !important;
            background-color: transparent !important;
            color: #EAF1FF !important;
            border: 0 !important;
            padding: 10px 14px !important;
            font-size: 0.95rem !important;
            caret-color: #60A5FA !important;
            -webkit-text-fill-color: #EAF1FF !important;
        }
        /* autofill: browsers force yellow bg — override */
        [data-testid="stTextInput"] input:-webkit-autofill,
        [data-baseweb="input"] input:-webkit-autofill {
            -webkit-box-shadow: 0 0 0 30px rgba(15,23,42,0.9) inset !important;
            -webkit-text-fill-color: #EAF1FF !important;
            caret-color: #60A5FA !important;
        }
        /* password dots — force high-contrast letter-spacing so they read as a mask */
        [data-testid="stTextInput"] input[type="password"],
        [data-baseweb="input"] input[type="password"],
        [data-baseweb="base-input"] input[type="password"] {
            letter-spacing: 0.2em !important;
            font-family: 'Courier New', monospace !important;
            font-size: 1.05rem !important;
        }
        [data-testid="stTextInput"] input::placeholder,
        [data-baseweb="input"] input::placeholder,
        [data-baseweb="base-input"] input::placeholder {
            color: rgba(143,176,230,0.55) !important;
            letter-spacing: normal !important;
            font-family: inherit !important;
        }

        /* password reveal (eye) button — transparent, subtle icon */
        [data-testid="stTextInput"] button,
        [data-baseweb="input"] button {
            background: transparent !important;
            color: #8FB0E6 !important;
            border: none !important;
        }
        [data-testid="stTextInput"] button svg,
        [data-baseweb="input"] button svg {
            fill: #8FB0E6 !important;
        }

        /* ── standard buttons ── */
        .stButton > button,
        [data-testid="stFormSubmitButton"] > button {
            background: linear-gradient(135deg, rgba(37,99,235,0.85), rgba(14,165,164,0.85)) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(96,165,250,0.35) !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            padding: 8px 20px !important;
            letter-spacing: 0.02em;
            transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
            box-shadow: 0 4px 14px rgba(37,99,235,0.25) !important;
        }
        .stButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            transform: translateY(-2px);
            border-color: rgba(96,165,250,0.6) !important;
            box-shadow: 0 8px 24px rgba(37,99,235,0.4) !important;
            color: #FFFFFF !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #EF4444, #F59E0B) !important;
            border-color: rgba(239,68,68,0.5) !important;
            box-shadow: 0 4px 14px rgba(239,68,68,0.28) !important;
        }
        .stButton > button[kind="primary"]:hover {
            box-shadow: 0 8px 24px rgba(239,68,68,0.45) !important;
        }

        /* ── link button ── */
        [data-testid="stLinkButton"] a {
            background: rgba(255,255,255,0.06) !important;
            color: #EAF1FF !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
            border-radius: 12px !important;
            font-weight: 500 !important;
            padding: 8px 18px !important;
            transition: background 0.2s, border-color 0.2s, transform 0.2s;
        }
        [data-testid="stLinkButton"] a:hover {
            background: rgba(96,165,250,0.15) !important;
            border-color: rgba(96,165,250,0.4) !important;
            transform: translateY(-1px);
            color: #EAF1FF !important;
        }
        [data-testid="stLinkButton"] a p { color: #EAF1FF !important; }

        /* ── checkboxes ── */
        [data-testid="stCheckbox"] label,
        [data-testid="stCheckbox"] label p { color: #EAF1FF !important; }
        [data-testid="stCheckbox"] [data-baseweb="checkbox"] div:first-child {
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.25) !important;
        }

        /* ── radio (PL/EN) ── */
        [data-testid="stRadio"] label,
        [data-testid="stRadio"] label p { color: #EAF1FF !important; }

        /* ── forms ── */
        [data-testid="stForm"] {
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            border-radius: 22px !important;
            background: rgba(255, 255, 255, 0.045) !important;
            padding: 28px !important;
            backdrop-filter: blur(14px) !important;
            -webkit-backdrop-filter: blur(14px) !important;
            box-shadow: 0 8px 32px rgba(0,0,0,0.25);
        }

        /* ── expanders (collapsed AND expanded) ── */
        [data-testid="stExpander"] {
            border: 1px solid rgba(255,255,255,0.10) !important;
            border-radius: 16px !important;
            background: rgba(255,255,255,0.035) !important;
            margin-bottom: 12px !important;
            backdrop-filter: blur(10px);
            transition: border-color 0.2s, background 0.2s;
            overflow: hidden;
        }
        [data-testid="stExpander"]:hover {
            border-color: rgba(96,165,250,0.3) !important;
        }
        /* summary bar — dark glass in BOTH collapsed and expanded state */
        [data-testid="stExpander"] > details > summary,
        [data-testid="stExpander"] > details[open] > summary,
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] details summary {
            background: rgba(15, 23, 42, 0.4) !important;
            border-bottom: 1px solid rgba(255,255,255,0.08) !important;
            padding: 12px 16px !important;
            border-radius: 16px 16px 0 0 !important;
        }
        [data-testid="stExpander"] > details:not([open]) > summary {
            border-bottom: 0 !important;
            border-radius: 16px !important;
        }
        [data-testid="stExpander"] summary:hover {
            background: rgba(96,165,250,0.12) !important;
        }
        /* summary text — force light color even inside newer Streamlit wrappers */
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary *,
        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] summary span,
        [data-testid="stExpander"] details summary *,
        [data-testid="stExpander"] details[open] summary * {
            color: #EAF1FF !important;
            font-weight: 600 !important;
            fill: #EAF1FF;
        }
        /* chevron icon */
        [data-testid="stExpander"] summary svg,
        [data-testid="stExpander"] details summary svg {
            fill: #8FB0E6 !important;
            color: #8FB0E6 !important;
        }
        /* expanded content area — keep dark */
        [data-testid="stExpander"] > details[open] > div,
        [data-testid="stExpander"] details[open] > div {
            background: transparent !important;
            padding: 16px !important;
        }

        /* ── dataframe (users table) ── */
        [data-testid="stDataFrame"] {
            border: 1px solid rgba(255,255,255,0.10) !important;
            border-radius: 16px !important;
            overflow: hidden;
            background: rgba(255,255,255,0.03) !important;
        }
        [data-testid="stDataFrame"] * {
            color: #EAF1FF !important;
        }
        [data-testid="stDataFrame"] [role="columnheader"],
        [data-testid="stDataFrame"] thead {
            background: rgba(96,165,250,0.15) !important;
            color: #EAF1FF !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em;
        }
        [data-testid="stDataFrame"] [role="row"]:hover {
            background: rgba(96,165,250,0.08) !important;
        }
        [data-testid="stDataFrame"] [data-testid="stTable"] { background: transparent !important; }

        /* ── divider ── */
        hr, [data-testid="stDivider"] {
            border-color: rgba(255,255,255,0.10) !important;
            margin: 24px 0 !important;
        }

        /* ── alerts ── */
        [data-testid="stAlert"] {
            background: rgba(255,255,255,0.05) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255,255,255,0.10) !important;
        }
        [data-testid="stAlert"] * { color: #EAF1FF !important; }

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
    """,
    unsafe_allow_html=True,
)


# ── Guard ─────────────────────────────────────────────────────────────────────
def _get_token() -> str:
    tok = st.query_params.get("token")
    if tok:
        st.session_state["token"] = tok
        return tok
    return st.session_state.get("token", "")


token = _get_token()
user = get_session_user(token) if token else None

if user is None:
    st.error("Brak autoryzacji. Zaloguj się w Business Intelligence Hub.")
    st.link_button("Wróć do Hub", url="/")
    st.stop()

if not user["is_admin"]:
    st.error("Nie masz uprawnień administratora.")
    st.link_button("Wróć do Hub", url=f"/?token={token}")
    st.stop()


# ── Language ──────────────────────────────────────────────────────────────────
TRANSLATIONS = {
    "PL": {
        "title": "Panel administratora",
        "subtitle": "Zarządzanie użytkownikami i uprawnieniami",
        "back": "◀ Wróć do Hub",
        "users_section": "Użytkownicy",
        "col_username": "Login",
        "col_admin": "Admin",
        "col_created": "Utworzony",
        "col_must_change": "Reset hasła",
        "col_actions": "Akcje",
        "add_user_section": "Dodaj użytkownika",
        "new_username": "Login",
        "new_password": "Hasło",
        "is_admin": "Administrator",
        "add_submit": "Dodaj",
        "user_added": "Użytkownik {u} został dodany.",
        "user_exists": "Użytkownik o takim loginie już istnieje.",
        "user_invalid": "Login i hasło są wymagane.",
        "delete_confirm": "Usuń użytkownika {u}?",
        "delete_yes": "Tak, usuń",
        "delete_no": "Anuluj",
        "reset_pw": "Reset hasła",
        "reset_pw_placeholder": "Nowe hasło",
        "reset_pw_submit": "Ustaw",
        "reset_pw_ok": "Hasło zresetowane. Użytkownik zostanie poproszony o zmianę przy następnym logowaniu.",
        "cannot_demote_last_admin": "Nie można odebrać uprawnień admina — musi zostać przynajmniej jeden administrator.",
        "cannot_delete_last_admin": "Nie można usunąć jedynego administratora.",
        "cannot_delete_self": "Nie możesz usunąć własnego konta.",
        "permissions_header": "Uprawnienia",
    },
    "EN": {
        "title": "Admin panel",
        "subtitle": "Manage users and permissions",
        "back": "◀ Back to Hub",
        "users_section": "Users",
        "col_username": "Username",
        "col_admin": "Admin",
        "col_created": "Created",
        "col_must_change": "Reset flag",
        "col_actions": "Actions",
        "add_user_section": "Add user",
        "new_username": "Username",
        "new_password": "Password",
        "is_admin": "Administrator",
        "add_submit": "Add",
        "user_added": "User {u} added.",
        "user_exists": "User with this username already exists.",
        "user_invalid": "Username and password are required.",
        "delete_confirm": "Delete user {u}?",
        "delete_yes": "Yes, delete",
        "delete_no": "Cancel",
        "reset_pw": "Reset password",
        "reset_pw_placeholder": "New password",
        "reset_pw_submit": "Set",
        "reset_pw_ok": "Password reset. User will be prompted to change on next login.",
        "cannot_demote_last_admin": "Cannot revoke admin — at least one administrator must remain.",
        "cannot_delete_last_admin": "Cannot delete the only administrator.",
        "cannot_delete_self": "You cannot delete your own account.",
        "permissions_header": "Permissions",
    },
}

lang_pref = st.session_state.get("hub_language", "PL")
_, lang_col = st.columns([5, 1])
with lang_col:
    language = st.radio(
        "Język / Language",
        ["PL", "EN"],
        horizontal=True,
        index=0 if lang_pref == "PL" else 1,
        key="admin_language",
    )
T = TRANSLATIONS[language]

st.markdown(f"# ⚙️ {T['title']}")
st.caption(T["subtitle"])
st.link_button(T["back"], url=f"/?token={token}")

st.divider()


# ── Users table ───────────────────────────────────────────────────────────────
st.subheader(T["users_section"])
users = list_users()

table_rows = []
for u in users:
    perms_display = ", ".join(APP_LABELS[a] for a in sorted(u["permissions"])) or "—"
    table_rows.append(
        {
            T["col_username"]: u["username"],
            T["col_admin"]: "✓" if u["is_admin"] else "",
            T["permissions_header"]: perms_display,
            T["col_must_change"]: "⚠" if u["must_change_password"] else "",
            T["col_created"]: u["created_at"][:10],
        }
    )

st.dataframe(pd.DataFrame(table_rows), hide_index=True, width="stretch")


# ── Per-user editing ──────────────────────────────────────────────────────────
st.subheader(T["permissions_header"])
for u in users:
    with st.expander(
        f"👤 {u['username']}" + (" · admin" if u["is_admin"] else ""), expanded=False
    ):
        col_perm, col_admin, col_pw, col_delete = st.columns([2, 1, 2, 1])

        with col_perm:
            st.caption(T["permissions_header"])
            for app in APPS:
                key = f"perm_{u['username']}_{app}"
                current = app in u["permissions"]
                new_val = st.checkbox(APP_LABELS[app], value=current, key=key)
                if new_val != current:
                    set_permission(u["username"], app, new_val)
                    st.rerun()

        with col_admin:
            st.caption(T["is_admin"])
            admin_key = f"admin_{u['username']}"
            new_admin = st.checkbox("", value=u["is_admin"], key=admin_key)
            if new_admin != u["is_admin"]:
                if not new_admin and count_admins() <= 1:
                    st.error(T["cannot_demote_last_admin"])
                else:
                    set_admin(u["username"], new_admin)
                    st.rerun()

        with col_pw:
            st.caption(T["reset_pw"])
            new_pw = st.text_input(
                T["reset_pw_placeholder"],
                type="password",
                key=f"pw_{u['username']}",
                label_visibility="collapsed",
            )
            if st.button(T["reset_pw_submit"], key=f"pw_btn_{u['username']}"):
                if new_pw and len(new_pw) >= 6:
                    change_password(u["username"], new_pw, clear_must_change=False)
                    st.success(T["reset_pw_ok"])
                else:
                    st.error("min. 6 znaków" if language == "PL" else "min. 6 chars")

        with col_delete:
            st.caption(" ")
            if u["username"] == user["username"]:
                st.caption(T["cannot_delete_self"])
            else:
                confirm_key = f"del_confirm_{u['username']}"
                if st.session_state.get(confirm_key):
                    if st.button(
                        T["delete_yes"],
                        key=f"del_yes_{u['username']}",
                        type="primary",
                    ):
                        if u["is_admin"] and count_admins() <= 1:
                            st.error(T["cannot_delete_last_admin"])
                            st.session_state[confirm_key] = False
                        else:
                            delete_user(u["username"])
                            st.session_state[confirm_key] = False
                            st.rerun()
                    if st.button(T["delete_no"], key=f"del_no_{u['username']}"):
                        st.session_state[confirm_key] = False
                        st.rerun()
                else:
                    if st.button("🗑 Usuń" if language == "PL" else "🗑 Delete", key=f"del_{u['username']}"):
                        st.session_state[confirm_key] = True
                        st.rerun()


# ── Add user ──────────────────────────────────────────────────────────────────
st.divider()
st.subheader(T["add_user_section"])
with st.form("add_user_form"):
    col_a, col_b, col_c, col_d = st.columns([2, 2, 1, 1])
    with col_a:
        new_username = st.text_input(T["new_username"])
    with col_b:
        new_password = st.text_input(T["new_password"], type="password")
    with col_c:
        make_admin = st.checkbox(T["is_admin"])
    with col_d:
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button(T["add_submit"], use_container_width=True)

    if submitted:
        if not new_username.strip() or not new_password:
            st.error(T["user_invalid"])
        elif not create_user(new_username, new_password, is_admin=make_admin):
            st.error(T["user_exists"])
        else:
            st.success(T["user_added"].format(u=new_username))
            st.rerun()
