"""
AI Exam Preparation Assistant  (Streamlit + Groq)
-------------------------------------------------
Features
  * Secure login / registration (PBKDF2 hashed passwords)
  * AI Doubt Solver (chat, optional grounding in your uploaded PDF/DOCX/TXT)
  * Personalized Study Plan generator
  * Automated Question Generator (MCQ + subjective, from topic or document)
  * Mock Tests (timed, auto-graded, with explanations and review)
  * Performance Analytics (trends, topic strengths/weaknesses, AI insights)
  * Document library (PDF / Word / TXT upload and text extraction)

Run:
    pip install -r requirements.txt
    export GROQ_API_KEY="gsk_..."          # or put it in .streamlit/secrets.toml
    streamlit run app.py

"""

import hashlib
import html
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import time
from datetime import date, datetime

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------- #
# Page config + styling
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="AI Exam Prep Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root{
      --brand:#4f46e5; --brand2:#7c3aed; --ink:#0f172a; --muted:#64748b;
      --line:#e2e8f0; --card:#ffffff; --shadow:0 1px 2px rgba(15,23,42,.05),0 8px 24px -12px rgba(15,23,42,.10);
    }
    html, body, .stApp, [class*="st-"], button, input, textarea, select {
      font-family:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
    }
    .stApp{background:#f6f7fb;}
    .block-container{padding-top:2rem; padding-bottom:3rem; max-width:1240px;}
    #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"]{display:none !important;}
    header[data-testid="stHeader"]{background:transparent;}
    h1,h2,h3,h4{letter-spacing:-.02em; color:var(--ink);}
    h4{font-weight:700;}

    /* ---------- Page header ---------- */
    .ph{display:flex; align-items:center; gap:.95rem; margin:0 0 1.4rem; padding-bottom:1.1rem;
        border-bottom:1px solid var(--line);}
    .ph .ic{width:48px; height:48px; border-radius:14px; display:flex; align-items:center; justify-content:center;
        font-size:1.45rem; background:linear-gradient(135deg,rgba(79,70,229,.14),rgba(124,58,237,.14));
        border:1px solid rgba(79,70,229,.22); flex-shrink:0;}
    .ph .t{font-size:1.55rem; font-weight:800; letter-spacing:-.025em; color:var(--ink); line-height:1.2;}
    .ph .s{color:var(--muted); font-size:.93rem; margin-top:.15rem;}

    /* ---------- Hero (dashboard) ---------- */
    .hero{position:relative; overflow:hidden; padding:1.9rem 2.1rem; border-radius:22px; color:#fff;
        background:linear-gradient(120deg,#4338ca 0%,#7c3aed 55%,#c026d3 100%);
        box-shadow:0 22px 44px -22px rgba(79,70,229,.65); margin-bottom:1.3rem;}
    .hero:before{content:""; position:absolute; right:-70px; top:-80px; width:300px; height:300px;
        border-radius:50%; background:rgba(255,255,255,.10);}
    .hero:after{content:""; position:absolute; right:120px; bottom:-120px; width:220px; height:220px;
        border-radius:50%; background:rgba(255,255,255,.07);}
    .hero .t{font-size:1.85rem; font-weight:800; letter-spacing:-.025em; color:#fff;}
    .hero .s{opacity:.92; margin-top:.3rem; font-size:1rem; color:#fff;}
    .hero .chips{margin-top:1rem; position:relative; z-index:2;}
    .hero .chips span{display:inline-block; background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.28);
        padding:.28rem .8rem; border-radius:999px; font-size:.82rem; font-weight:600; margin:0 .4rem .3rem 0; color:#fff;}

    /* ---------- KPI cards ---------- */
    .kpis{display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin-bottom:1.3rem;}
    .kpi{background:var(--card); border:1px solid var(--line); border-radius:18px; padding:1.05rem 1.2rem;
        box-shadow:var(--shadow);}
    .kpi .l{display:flex; justify-content:space-between; font-size:.74rem; text-transform:uppercase;
        letter-spacing:.07em; color:var(--muted); font-weight:700;}
    .kpi .v{font-size:2rem; font-weight:800; letter-spacing:-.03em; color:var(--ink); margin-top:.25rem;}
    .kpi .d{font-size:.8rem; color:var(--muted); margin-top:.05rem;}
    @media (max-width:900px){ .kpis{grid-template-columns:repeat(2,1fr);} }

    /* ---------- Cards, chips, lists ---------- */
    .card{background:var(--card); border:1px solid var(--line); border-radius:18px; padding:1.1rem 1.25rem;
        box-shadow:var(--shadow); margin-bottom:.9rem;}
    .ac b{display:block; font-size:1.02rem; margin:.45rem 0 .1rem; color:var(--ink);}
    .ac p{margin:0 0 .6rem; color:var(--muted); font-size:.87rem;}
    .ac .ai{display:inline-flex; width:40px; height:40px; align-items:center; justify-content:center;
        border-radius:12px; background:rgba(79,70,229,.10); font-size:1.2rem;}
    .chip{display:inline-block; padding:.22rem .7rem; border-radius:999px; font-size:.78rem; font-weight:600;
        background:rgba(79,70,229,.10); color:#4338ca; margin:.12rem .25rem .12rem 0;}
    .chip.bad{background:rgba(239,68,68,.10); color:#b91c1c;}
    .chip.good{background:rgba(16,185,129,.12); color:#047857;}
    .act{display:flex; justify-content:space-between; gap:.8rem; padding:.55rem 0; border-bottom:1px dashed var(--line);
        font-size:.9rem; color:var(--ink);}
    .act:last-child{border-bottom:none;}
    .act small{color:var(--muted); white-space:nowrap;}
    .empty{text-align:center; color:var(--muted); padding:1.6rem .5rem; font-size:.92rem;}
    .announce{display:flex; gap:.7rem; align-items:flex-start; background:#fffbeb; border:1px solid #fde68a;
        color:#92400e; padding:.8rem 1rem; border-radius:14px; margin-bottom:1.1rem; font-size:.93rem;}

    /* ---------- Streamlit widgets ---------- */
    div[data-testid="stMetric"]{background:var(--card); border:1px solid var(--line); border-radius:16px;
        padding:.9rem 1.1rem; box-shadow:var(--shadow);}
    div[data-testid="stMetricLabel"] p{color:var(--muted); font-weight:600; font-size:.82rem;}
    div[data-testid="stMetricValue"]{font-weight:800; letter-spacing:-.02em;}
    .stButton>button, .stDownloadButton>button, .stFormSubmitButton>button{
      border-radius:11px; font-weight:600; border:1px solid var(--line); background:#fff; color:var(--ink);
      padding:.5rem 1rem; transition:all .15s ease;}
    .stButton>button:hover, .stDownloadButton>button:hover, .stFormSubmitButton>button:hover{
      border-color:var(--brand); color:var(--brand); transform:translateY(-1px);
      box-shadow:0 8px 18px -8px rgba(79,70,229,.45);}
    button[kind="primary"], button[kind="primaryFormSubmit"]{
      background:linear-gradient(135deg,var(--brand),var(--brand2)) !important; color:#fff !important; border:none !important;}
    button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover{filter:brightness(1.06); color:#fff !important;}
    [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"]>div{border-radius:11px !important;}
    .stTabs [data-baseweb="tab-list"]{gap:.3rem; border-bottom:1px solid var(--line);}
    .stTabs [data-baseweb="tab"]{padding:.55rem 1.05rem; font-weight:600; border-radius:10px 10px 0 0;}
    div[data-testid="stExpander"]{background:var(--card); border:1px solid var(--line) !important;
        border-radius:14px; box-shadow:var(--shadow);}
    div[data-testid="stChatMessage"]{background:var(--card); border:1px solid var(--line); border-radius:16px;
        padding:.9rem 1.1rem; box-shadow:var(--shadow);}
    div[data-testid="stForm"]{background:var(--card); border:1px solid var(--line); border-radius:18px;
        padding:1.3rem; box-shadow:var(--shadow);}
    div[data-testid="stDataFrame"]{border:1px solid var(--line); border-radius:14px; overflow:hidden;}

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0f172a 0%,#1e1b4b 100%);
        border-right:none;}
    section[data-testid="stSidebar"] *{color:#e2e8f0;}
    section[data-testid="stSidebar"] svg{fill:#e2e8f0;}
    section[data-testid="stSidebar"] .brand{display:flex; align-items:center; gap:.7rem; margin:.2rem 0 1rem;}
    section[data-testid="stSidebar"] .logo{width:42px; height:42px; border-radius:12px; display:flex;
        align-items:center; justify-content:center; font-size:1.3rem;
        background:linear-gradient(135deg,#6366f1,#c026d3);}
    section[data-testid="stSidebar"] .bn{font-weight:800; font-size:1.1rem; color:#fff; letter-spacing:-.02em;}
    section[data-testid="stSidebar"] .bs{font-size:.74rem; color:#94a3b8;}
    section[data-testid="stSidebar"] .uchip{display:flex; align-items:center; gap:.65rem; padding:.65rem .75rem;
        border-radius:14px; background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.10); margin-bottom:1rem;}
    section[data-testid="stSidebar"] .av{width:36px; height:36px; border-radius:50%; display:flex; align-items:center;
        justify-content:center; font-weight:700; font-size:.85rem; color:#fff;
        background:linear-gradient(135deg,#06b6d4,#6366f1);}
    section[data-testid="stSidebar"] .un{font-weight:700; color:#fff; font-size:.92rem;}
    section[data-testid="stSidebar"] .ur{font-size:.74rem; color:#94a3b8;}
    section[data-testid="stSidebar"] .side-h{font-size:.68rem; letter-spacing:.12em; font-weight:700;
        color:#94a3b8; margin:1.2rem 0 .5rem;}
    section[data-testid="stSidebar"] .pill{display:inline-block; padding:.28rem .7rem; border-radius:999px;
        font-size:.76rem; font-weight:600; margin-bottom:.6rem;}
    section[data-testid="stSidebar"] .pill.ok{background:rgba(16,185,129,.15); color:#34d399;}
    section[data-testid="stSidebar"] div[role="radiogroup"]{gap:.15rem;}
    section[data-testid="stSidebar"] div[role="radiogroup"] label{padding:.58rem .85rem; border-radius:11px;
        width:100%; cursor:pointer; transition:background .15s ease;}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover{background:rgba(255,255,255,.08);}
    section[data-testid="stSidebar"] label[data-baseweb="radio"]>div:first-child{display:none;}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){
        background:linear-gradient(90deg,#4f46e5,#7c3aed); box-shadow:0 8px 18px -8px rgba(99,102,241,.7);}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) *{color:#fff; font-weight:700;}
    section[data-testid="stSidebar"] [data-baseweb="input"], section[data-testid="stSidebar"] [data-baseweb="select"]>div{
        background:rgba(255,255,255,.08) !important; border-color:rgba(255,255,255,.18) !important;}
    section[data-testid="stSidebar"] input{color:#fff !important;}
    section[data-testid="stSidebar"] .stButton>button{background:rgba(255,255,255,.08); color:#fff;
        border:1px solid rgba(255,255,255,.2);}
    section[data-testid="stSidebar"] .stButton>button:hover{background:rgba(255,255,255,.16); color:#fff;
        border-color:rgba(255,255,255,.4); box-shadow:none;}

    /* ---------- Sidebar always visible on desktop ---------- */
    @media (min-width: 769px){
      section[data-testid="stSidebar"]{
        transform:none !important; margin-left:0 !important; visibility:visible !important;
        min-width:300px !important; width:300px !important; max-width:300px !important;}
      [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"],
      [data-testid="collapsedControl"], button[kind="headerNoPadding"]{display:none !important;}
      section[data-testid="stSidebar"] [data-testid="stSidebarResizeHandle"]{display:none !important;}
    }
    /* mobile: make the hamburger clearly visible */
    @media (max-width: 768px){
      [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"]{
        background:#fff; border:1px solid var(--line); border-radius:12px; box-shadow:var(--shadow);
        z-index:999999; top:.6rem; left:.6rem;}
      [data-testid="stSidebarCollapsedControl"] svg, [data-testid="collapsedControl"] svg{fill:#0f172a;}
    }
    .backbar{margin:-.4rem 0 .9rem;}

    /* ---------- Auth page ---------- */
    .brand-panel{border-radius:26px; padding:2.4rem 2.2rem; color:#fff; min-height:600px; position:relative; overflow:hidden;
        background:linear-gradient(150deg,#312e81 0%,#6d28d9 58%,#be185d 100%);
        box-shadow:0 30px 60px -28px rgba(79,70,229,.7);}
    .brand-panel:before{content:""; position:absolute; right:-90px; top:-90px; width:320px; height:320px;
        border-radius:50%; background:rgba(255,255,255,.09);}
    .brand-panel *{color:#fff; position:relative;}
    .bp-logo{font-size:1.25rem; font-weight:800; letter-spacing:-.02em; margin-bottom:2.2rem;}
    .bp-h{font-size:2.15rem; font-weight:800; line-height:1.15; letter-spacing:-.03em;}
    .bp-s{opacity:.88; margin:.8rem 0 1.6rem; font-size:1rem;}
    .bp-list{list-style:none; padding:0; margin:0 0 1.8rem;}
    .bp-list li{display:flex; gap:.8rem; margin-bottom:.95rem; align-items:flex-start;}
    .bp-list .dot{flex-shrink:0; width:30px; height:30px; border-radius:10px; background:rgba(255,255,255,.18);
        display:flex; align-items:center; justify-content:center; font-size:.95rem;}
    .bp-list b{display:block; font-size:.95rem;}
    .bp-list span.d{opacity:.82; font-size:.84rem;}
    .bp-stats{display:flex; gap:1.6rem; border-top:1px solid rgba(255,255,255,.22); padding-top:1.2rem;}
    .bp-stats b{display:block; font-size:1.35rem; font-weight:800;}
    .bp-stats span{font-size:.78rem; opacity:.8;}
    .auth-title{font-size:1.7rem; font-weight:800; letter-spacing:-.025em; color:var(--ink); margin-top:.6rem;}
    .auth-sub{color:var(--muted); margin:.2rem 0 1rem;}
    .trust{text-align:center; color:var(--muted); font-size:.8rem; margin-top:.9rem;}
    .footer{text-align:center; color:#94a3b8; font-size:.8rem; margin-top:2.5rem; padding-top:1rem;
        border-top:1px solid var(--line);}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
DB_PATH = os.environ.get("EXAMPREP_DB", "examprep.db")
# Ordered best -> fallback. The app automatically uses the first one that works.
MODELS = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
]
EXAMS = [
    "JEE (Main/Advanced)", "NEET", "UPSC", "GATE", "CAT", "SSC", "Banking (IBPS/SBI)",
    "CBSE Board", "State Board", "SAT", "GRE", "GMAT", "IELTS/TOEFL", "University Semester Exam", "Other",
]
MAX_DOC_CHARS = 400_000


# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def run(sql, params=(), fetch=None):
    """fetch: None | 'one' | 'all' | 'id'"""
    conn = db()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        if fetch == "one":
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch == "all":
            return [dict(r) for r in cur.fetchall()]
        if fetch == "id":
            return cur.lastrowid
        return None
    finally:
        conn.close()


def df_query(sql, params=()):
    conn = db()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def init_db():
    conn = db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL,
            pw_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            active INTEGER NOT NULL DEFAULT 1,
            target_exam TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            last_login TEXT
        );
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS documents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, filename TEXT, filetype TEXT,
            chars INTEGER, content TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS doubts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, subject TEXT, question TEXT, answer TEXT,
            doc_id INTEGER, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS study_plans(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, exam TEXT, exam_date TEXT, hours_per_day REAL,
            inputs TEXT, plan TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS question_bank(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, exam TEXT, topic TEXT, difficulty TEXT, qtype TEXT,
            payload TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS tests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, title TEXT, exam TEXT, topic TEXT, difficulty TEXT,
            time_limit_min INTEGER, questions TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS attempts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, test_id INTEGER, score INTEGER, total INTEGER,
            duration_sec INTEGER, overtime INTEGER DEFAULT 0,
            answers TEXT, topic_stats TEXT, created_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def get_setting(key, default=""):
    row = run("SELECT value FROM settings WHERE key=?", (key,), fetch="one")
    return row["value"] if row else default


def set_setting(key, value):
    run("INSERT INTO settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
def hash_pw(password, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
    return salt, h.hex()


def create_user(username, email, password, role="user"):
    salt, h = hash_pw(password)
    return run(
        "INSERT INTO users(username,email,salt,pw_hash,role,created_at) VALUES(?,?,?,?,?,?)",
        (username.strip(), email.strip().lower(), salt, h, role, now()),
        fetch="id",
    )


def authenticate(identifier, password):
    u = run("SELECT * FROM users WHERE username=? OR email=?",
            (identifier.strip(), identifier.strip().lower()), fetch="one")
    if not u:
        return None, "Invalid credentials."
    _, h = hash_pw(password, u["salt"])
    if not hmac.compare_digest(h, u["pw_hash"]):
        return None, "Invalid credentials."
    if not u["active"]:
        return None, "This account is deactivated."
    run("UPDATE users SET last_login=? WHERE id=?", (now(), u["id"]))
    return u, None


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def current_user():
    return st.session_state.get("user")


def auth_page():
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown(
            """
            <div class="brand-panel">
              <div class="bp-logo">🎓 ExamPrep AI</div>
              <div class="bp-h">Your personal AI coach for every exam.</div>
              <div class="bp-s">Learn faster with an AI tutor, tailored study plans and unlimited practice tests.</div>
              <ul class="bp-list">
                <li><div class="dot">💬</div><div><b>AI Doubt Solver</b>
                    <span class="d">Step-by-step answers, grounded in your own notes</span></div></li>
                <li><div class="dot">🗓️</div><div><b>Personalized Study Plans</b>
                    <span class="d">Day-by-day roadmaps built around your exam date</span></div></li>
                <li><div class="dot">📝</div><div><b>Mock Tests &amp; Question Generator</b>
                    <span class="d">Auto-generated, auto-graded, with explanations</span></div></li>
                <li><div class="dot">📊</div><div><b>Performance Analytics</b>
                    <span class="d">Find weak topics and track progress over time</span></div></li>
              </ul>
              <div class="bp-stats">
                <div><b>15+</b><span>Exam categories</span></div>
                <div><b>24/7</b><span>AI tutor</span></div>
                <div><b>Instant</b><span>Auto-grading</span></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            '<div class="auth-title">Welcome 👋</div>'
            '<div class="auth-sub">Sign in or create an account to continue your preparation.</div>',
            unsafe_allow_html=True,
        )
        tab_login, tab_reg = st.tabs(["Sign in", "Create account"])
        with tab_login:
            with st.form("login_form"):
                ident = st.text_input("Username or email", placeholder="you@example.com")
                pw = st.text_input("Password", type="password", placeholder="••••••••")
                ok = st.form_submit_button("Sign in", width="stretch", type="primary")
            if ok:
                user, err = authenticate(ident, pw)
                if err:
                    st.error(err)
                else:
                    st.session_state.user = user
                    st.rerun()
        with tab_reg:
            if True:
                with st.form("reg_form"):
                    un = st.text_input("Username")
                    em = st.text_input("Email")
                    exam = st.selectbox("Target exam", EXAMS)
                    p1 = st.text_input("Password (min 8 chars)", type="password")
                    p2 = st.text_input("Confirm password", type="password")
                    go = st.form_submit_button("Create account", width="stretch", type="primary")
                if go:
                    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", un or ""):
                        st.error("Username: 3-30 chars, letters/numbers/._- only.")
                    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", em or ""):
                        st.error("Enter a valid email address.")
                    elif len(p1) < 8:
                        st.error("Password must be at least 8 characters.")
                    elif p1 != p2:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            uid = create_user(un, em, p1)
                            run("UPDATE users SET target_exam=? WHERE id=?", (exam, uid))
                            st.success("Account created! Switch to the Sign in tab to log in.")
                        except sqlite3.IntegrityError:
                            st.error("Username or email already registered.")
        st.markdown('<div class="trust">🔒 Passwords are salted &amp; hashed · Your data stays private</div>',
                    unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Groq / LLM helpers
# --------------------------------------------------------------------------- #
def _dotenv_key():
    """Read GROQ_API_KEY from a .env file placed next to app.py."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GROQ_API_KEY") and "=" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return None


def _secret_key():
    try:
        return st.secrets.get("GROQ_API_KEY")
    except Exception:
        return None


def get_api_key():
    """Priority: env var -> Streamlit secrets -> .env file."""
    return os.environ.get("GROQ_API_KEY") or _secret_key() or _dotenv_key() or None


def model_order():
    return list(MODELS)


def llm(messages, json_mode=False, temperature=0.4, max_tokens=4096):
    """Call Groq using the best available model, falling back automatically."""
    key = get_api_key()
    if not key:
        raise RuntimeError("The AI service is not configured yet. Please set GROQ_API_KEY "
                           "in the .env file and restart the app.")
    try:
        from groq import Groq
    except ImportError:
        raise RuntimeError("The `groq` package is missing. Run: pip install groq")
    client = Groq(api_key=key)
    last_err = None
    for model in model_order():
        kwargs = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
        try:
            if json_mode:
                try:
                    resp = client.chat.completions.create(response_format={"type": "json_object"}, **kwargs)
                except Exception:
                    resp = client.chat.completions.create(**kwargs)
            else:
                resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "401" in msg or "invalid api key" in msg or "authentication" in msg:
                raise RuntimeError("The Groq API key is invalid. Please check GROQ_API_KEY in your .env file.")
            continue  # model unavailable / rate-limited -> try next one
    raise RuntimeError(f"Groq API error: {last_err}")


def parse_json(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e > s:
            return json.loads(text[s:e + 1])
        raise ValueError("The model did not return valid JSON. Try again.")


# --------------------------------------------------------------------------- #
# Documents: extraction + retrieval
# --------------------------------------------------------------------------- #
def extract_text(uploaded):
    name = uploaded.name.lower()
    data = uploaded.getvalue()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages), "pdf"
    if name.endswith(".docx"):
        import docx
        d = docx.Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts), "docx"
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="ignore"), "txt"
    raise ValueError("Unsupported file type. Upload PDF, DOCX, TXT or MD.")


def user_docs(uid):
    return run("SELECT id, filename, filetype, chars, created_at FROM documents "
               "WHERE user_id=? ORDER BY id DESC", (uid,), fetch="all")


def doc_text(doc_id, uid=None):
    sql, params = "SELECT content FROM documents WHERE id=?", [doc_id]
    if uid is not None:
        sql += " AND user_id=?"
        params.append(uid)
    row = run(sql, tuple(params), fetch="one")
    return row["content"] if row else ""


def chunk(text, size=1500):
    return [text[i:i + size] for i in range(0, len(text), size)]


def relevant_context(text, query, k=4):
    chunks = chunk(text)
    if len(chunks) <= k:
        return "\n---\n".join(chunks)
    words = set(re.findall(r"[a-z0-9]{3,}", query.lower()))
    scored = sorted(chunks, key=lambda c: -len(words & set(re.findall(r"[a-z0-9]{3,}", c.lower()))))
    return "\n---\n".join(scored[:k])


def spread_context(text, limit=12000):
    if len(text) <= limit:
        return text
    chunks = chunk(text, 2000)
    n = max(1, limit // 2000)
    step = max(1, len(chunks) // n)
    return "\n---\n".join(chunks[::step][:n])


def doc_picker(label, key, uid):
    docs = user_docs(uid)
    opts = {0: "— none —"}
    opts.update({d["id"]: f"{d['filename']} ({d['chars']:,} chars)" for d in docs})
    return st.selectbox(label, list(opts.keys()), format_func=lambda x: opts[x], key=key)


# --------------------------------------------------------------------------- #
# Shared UI helpers
# --------------------------------------------------------------------------- #
def header(title, subtitle=""):
    icon, _, text = title.partition(" ")
    if not icon or icon[0].isalnum():
        icon, text = "🎓", title
    st.markdown(
        f'<div class="ph"><div class="ic">{icon}</div><div><div class="t">{text}</div>'
        f'<div class="s">{subtitle}</div></div></div>',
        unsafe_allow_html=True,
    )


def safe_call(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception as e:
        st.error(str(e))
        return None


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def goto(page):
    st.session_state["nav"] = page


def kpi(label, value, sub="", icon=""):
    return (f'<div class="kpi"><div class="l"><span>{label}</span><span>{icon}</span></div>'
            f'<div class="v">{value}</div><div class="d">{sub}</div></div>')


def greeting():
    h = datetime.now().hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"


def page_dashboard():
    u = current_user()
    uid = u["id"]
    att = df_query("SELECT * FROM attempts WHERE user_id=? ORDER BY id", (uid,))
    doubts = run("SELECT COUNT(*) c FROM doubts WHERE user_id=?", (uid,), fetch="one")["c"]
    docs = run("SELECT COUNT(*) c FROM documents WHERE user_id=?", (uid,), fetch="one")["c"]
    plan = run("SELECT * FROM study_plans WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,), fetch="one")

    # ---- hero ----
    chips = f'<span>🎯 {html.escape(u["target_exam"] or "Set your target exam in Profile")}</span>'
    if plan and plan["exam_date"]:
        try:
            days = (datetime.strptime(plan["exam_date"], "%Y-%m-%d").date() - date.today()).days
            chips += f'<span>⏳ {max(days, 0)} days to {html.escape(plan["exam"])}</span>'
        except ValueError:
            pass
    st.markdown(
        f'<div class="hero"><div class="t">{greeting()}, {html.escape(u["username"])} 👋</div>'
        f'<div class="s">Here is your preparation snapshot. Keep the momentum going!</div>'
        f'<div class="chips">{chips}</div></div>',
        unsafe_allow_html=True,
    )
    # ---- KPIs ----
    if len(att):
        att["pct"] = (att["score"] / att["total"] * 100).round(1)
        avg, best = f"{att['pct'].mean():.0f}%", f"{att['pct'].max():.0f}%"
    else:
        avg, best = "—", "—"
    st.markdown(
        '<div class="kpis">'
        + kpi("Tests taken", len(att), "mock tests completed", "📝")
        + kpi("Average score", avg, "across all attempts", "🎯")
        + kpi("Best score", best, "your personal record", "🏆")
        + kpi("Doubts solved", doubts, f"{docs} document(s) in library", "💬")
        + "</div>",
        unsafe_allow_html=True,
    )

    # ---- trend + focus/activity ----
    c_left, c_right = st.columns([3, 2], gap="large")
    with c_left:
        with st.container(border=True):
            st.markdown("#### 📈 Score trend")
            if len(att):
                st.line_chart(att.set_index("created_at")["pct"], height=260)
            else:
                st.markdown('<div class="empty">No attempts yet.<br>Take a mock test to see your progress here.</div>',
                            unsafe_allow_html=True)
    with c_right:
        with st.container(border=True):
            st.markdown("#### 🎯 Focus areas")
            agg = {}
            for s in att["topic_stats"] if len(att) else []:
                for k, v in json.loads(s or "{}").items():
                    a = agg.setdefault(k, [0, 0])
                    a[0] += v[0]
                    a[1] += v[1]
            if agg:
                ranked = sorted(agg.items(), key=lambda kv: kv[1][0] / kv[1][1])
                weak = [k for k, v in ranked if v[0] / v[1] < 0.6][:5]
                strong = [k for k, v in ranked[::-1] if v[0] / v[1] >= 0.8][:5]
                st.markdown("".join(f'<span class="chip bad">{html.escape(k)}</span>' for k in weak)
                            or '<span class="chip">No weak topics 🎉</span>', unsafe_allow_html=True)
                if strong:
                    st.markdown("".join(f'<span class="chip good">{html.escape(k)}</span>' for k in strong),
                                unsafe_allow_html=True)
            else:
                st.markdown('<div class="empty">Topic insights appear after your first test.</div>',
                            unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("#### 🕒 Recent activity")
            acts = []
            for r in run("SELECT a.score,a.total,a.created_at,t.title FROM attempts a "
                         "LEFT JOIN tests t ON t.id=a.test_id WHERE a.user_id=? ORDER BY a.id DESC LIMIT 4",
                         (uid,), fetch="all"):
                acts.append((r["created_at"], f"📝 {html.escape(r['title'] or 'Test')} — {r['score']}/{r['total']}"))
            for r in run("SELECT question, created_at FROM doubts WHERE user_id=? ORDER BY id DESC LIMIT 4",
                         (uid,), fetch="all"):
                acts.append((r["created_at"], f"💬 {html.escape(r['question'][:48])}…"))
            acts = sorted(acts, reverse=True)[:5]
            if acts:
                st.markdown("".join(f'<div class="act"><span>{t}</span><small>{d[5:16]}</small></div>'
                                    for d, t in acts), unsafe_allow_html=True)
            else:
                st.markdown('<div class="empty">Nothing yet — ask a doubt or start a test!</div>',
                            unsafe_allow_html=True)

    # ---- quick actions ----
    st.markdown("#### 🚀 Jump back in")
    actions = [
        ("💬", "Ask a doubt", "Step-by-step AI explanations", "💬 Doubt Solver"),
        ("📝", "Take a mock test", "AI-generated, auto-graded", "📝 Mock Tests"),
        ("🗓️", "Build a study plan", "Tailored to your exam date", "🗓️ Study Plan"),
        ("🧠", "Generate questions", "From a topic or your notes", "🧠 Question Generator"),
        ("📁", "Upload notes", "PDF, Word or text files", "📁 Documents"),
        ("📊", "View analytics", "Strengths, weaknesses, trends", "📊 Analytics"),
    ]
    cols = st.columns(3)
    for i, (ic, t, d, pg) in enumerate(actions):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f'<div class="ac"><span class="ai">{ic}</span><b>{t}</b><p>{d}</p></div>',
                            unsafe_allow_html=True)
                st.button("Open →", key=f"qa{i}", on_click=goto, args=(pg,), width="stretch")


# ---------- Doubt solver ---------- #
def page_doubts():
    u = current_user()
    header("💬 AI Doubt Solver", "Ask anything. Optionally ground answers in your uploaded notes.")
    tab_chat, tab_hist = st.tabs(["Chat", "History"])

    with tab_chat:
        c1, c2, c3 = st.columns([2, 2, 1])
        subject = c1.text_input("Subject / topic", value="General", key="d_subject")
        doc_id = c2.selectbox(
            "Use a document (optional)",
            [0] + [d["id"] for d in user_docs(u["id"])],
            format_func=lambda i: "— none —" if i == 0 else
            next(d["filename"] for d in user_docs(u["id"]) if d["id"] == i),
            key="d_doc",
        )
        level = c3.selectbox("Level", ["Beginner", "Intermediate", "Advanced"], index=1)
        if st.button("🧹 Clear chat"):
            st.session_state.chat = []
            st.rerun()

        st.session_state.setdefault("chat", [])
        for m in st.session_state.chat:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        prompt = st.chat_input("Type your doubt here…")
        if prompt:
            st.session_state.chat.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            system = (
                "You are an expert, patient exam-preparation tutor. Explain step by step, "
                "use simple language suited to a {lvl} learner, show formulas and worked "
                "examples where relevant (use LaTeX with $...$ for math), point out common "
                "mistakes, and end with a one-line key takeaway. Subject: {sub}."
            ).format(lvl=level.lower(), sub=subject)
            msgs = [{"role": "system", "content": system}]
            if doc_id:
                ctx = relevant_context(doc_text(doc_id, u["id"]), prompt)
                msgs.append({"role": "system", "content":
                             "Use the following study material as the primary source when relevant. "
                             "If the answer is not in it, say so and answer from general knowledge.\n\n" + ctx})
            msgs += st.session_state.chat[-10:]
            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    ans = safe_call(llm, msgs, temperature=0.3)
                if ans:
                    st.markdown(ans)
                    st.session_state.chat.append({"role": "assistant", "content": ans})
                    run("INSERT INTO doubts(user_id,subject,question,answer,doc_id,created_at) VALUES(?,?,?,?,?,?)",
                        (u["id"], subject, prompt, ans, doc_id or None, now()))

    with tab_hist:
        rows = run("SELECT * FROM doubts WHERE user_id=? ORDER BY id DESC LIMIT 100", (u["id"],), fetch="all")
        if not rows:
            st.caption("No doubts asked yet.")
        for r in rows:
            with st.expander(f"[{r['subject']}] {r['question'][:90]}  —  {r['created_at']}"):
                st.markdown(f"**Q:** {r['question']}")
                st.markdown(r["answer"])


# ---------- Study plan ---------- #
def page_plan():
    u = current_user()
    header("🗓️ Personalized Study Plan", "A day-by-day roadmap built around your exam date, time and weak areas.")
    tab_new, tab_saved = st.tabs(["Create plan", "Saved plans"])
    with tab_new:
        with st.form("plan_form"):
            c1, c2 = st.columns(2)
            exam = c1.selectbox("Exam", EXAMS, index=EXAMS.index(u["target_exam"]) if u["target_exam"] in EXAMS else 0)
            exam_date = c2.date_input("Exam date", value=date.today().replace(year=date.today().year + (1 if date.today().month > 9 else 0)))
            c3, c4 = st.columns(2)
            hours = c3.slider("Study hours per day", 1.0, 14.0, 4.0, 0.5)
            level = c4.selectbox("Current level", ["Beginner", "Intermediate", "Advanced"], index=1)
            subjects = st.text_input("Subjects / syllabus focus", placeholder="Physics, Chemistry, Maths")
            weak = st.text_area("Weak topics", placeholder="Thermodynamics, Organic reactions…")
            strong = st.text_area("Strong topics", placeholder="Algebra, Mechanics…")
            extra = st.text_input("Other constraints", placeholder="Weekends off, college 9-4, coaching on Sat…")
            go = st.form_submit_button("✨ Generate plan", type="primary", width="stretch")
        if go:
            days_left = (exam_date - date.today()).days
            if days_left < 1:
                st.error("Choose a future exam date.")
            else:
                prompt = f"""Create a detailed personalized study plan.
Exam: {exam}
Today: {date.today()}   Exam date: {exam_date}   Days left: {days_left}
Study hours/day: {hours}   Level: {level}
Subjects: {subjects or 'full syllabus'}
Weak topics: {weak or 'not specified'}
Strong topics: {strong or 'not specified'}
Constraints: {extra or 'none'}

Output in Markdown with:
1. Strategy overview and phase breakdown (Foundation, Practice, Revision, Mock-test phase) with date ranges.
2. A week-by-week table (Week | Dates | Focus topics | Goals | Mock test).
3. A sample daily timetable with time blocks adding up to {hours} hours.
4. Revision and spaced-repetition schedule.
5. Weak-topic remediation plan, with extra time allocated.
6. Weekly self-assessment checkpoints and tips for the last 7 days."""
                with st.spinner("Designing your plan…"):
                    plan = safe_call(llm, [
                        {"role": "system", "content": "You are an expert academic coach and exam strategist."},
                        {"role": "user", "content": prompt}], temperature=0.5, max_tokens=6000)
                if plan:
                    inputs = json.dumps(dict(subjects=subjects, weak=weak, strong=strong, level=level, extra=extra))
                    run("INSERT INTO study_plans(user_id,exam,exam_date,hours_per_day,inputs,plan,created_at) "
                        "VALUES(?,?,?,?,?,?,?)",
                        (u["id"], exam, str(exam_date), hours, inputs, plan, now()))
                    st.success("Plan saved!")
                    st.markdown(plan)
                    st.download_button("⬇️ Download plan (.md)", plan, file_name="study_plan.md")
    with tab_saved:
        rows = run("SELECT * FROM study_plans WHERE user_id=? ORDER BY id DESC", (u["id"],), fetch="all")
        if not rows:
            st.caption("No saved plans.")
        for r in rows:
            with st.expander(f"{r['exam']} — exam {r['exam_date']} — created {r['created_at']}"):
                st.markdown(r["plan"])
                cc1, cc2 = st.columns(2)
                cc1.download_button("⬇️ Download", r["plan"], file_name=f"plan_{r['id']}.md", key=f"dl{r['id']}")
                if cc2.button("🗑️ Delete", key=f"delp{r['id']}"):
                    run("DELETE FROM study_plans WHERE id=? AND user_id=?", (r["id"], u["id"]))
                    st.rerun()


# ---------- Question generation ---------- #
def generate_questions(exam, topic, n, difficulty, qtype, context=""):
    if qtype == "MCQ":
        schema = ('{"questions":[{"question":"...","options":["A text","B text","C text","D text"],'
                  '"answer":0,"explanation":"...","topic":"sub-topic","difficulty":"easy|medium|hard"}]}')
        rule = "Each question has exactly 4 options; 'answer' is the 0-based index of the correct option."
    else:
        schema = ('{"questions":[{"question":"...","model_answer":"...","marks":5,'
                  '"topic":"sub-topic","difficulty":"easy|medium|hard"}]}')
        rule = "Provide a complete model answer and marks for each question."
    src = f"\n\nBase the questions ONLY on this study material:\n{context}" if context else ""
    prompt = (f"Generate {n} {difficulty} {qtype} questions for the exam '{exam}' on the topic '{topic}'. "
              f"{rule} Questions must be accurate, unambiguous and exam-style. "
              f"Return ONLY valid JSON in this exact shape: {schema}{src}")
    out = llm([{"role": "system", "content": "You are an expert exam paper setter. Output JSON only."},
               {"role": "user", "content": prompt}], json_mode=True, temperature=0.6, max_tokens=6000)
    data = parse_json(out)
    qs = data.get("questions", data if isinstance(data, list) else [])
    clean = []
    for q in qs:
        if not q.get("question"):
            continue
        if qtype == "MCQ":
            opts = q.get("options") or []
            ans = q.get("answer")
            if isinstance(ans, str):
                ans = "ABCD".find(ans.strip().upper()[:1]) if ans.strip()[:1].upper() in "ABCD" else -1
            if len(opts) < 2 or not isinstance(ans, int) or not (0 <= ans < len(opts)):
                continue
            q["options"], q["answer"] = [str(o) for o in opts], ans
        q.setdefault("topic", topic)
        q.setdefault("difficulty", difficulty.lower())
        clean.append(q)
    if not clean:
        raise ValueError("No valid questions were generated. Please try again.")
    return clean


def page_questions():
    u = current_user()
    header("🧠 Question Generator", "Create practice questions from a topic or from your own notes.")
    with st.form("qgen"):
        c1, c2 = st.columns(2)
        exam = c1.selectbox("Exam", EXAMS, index=EXAMS.index(u["target_exam"]) if u["target_exam"] in EXAMS else 0)
        topic = c2.text_input("Topic", placeholder="Newton's laws of motion")
        c3, c4, c5 = st.columns(3)
        n = c3.slider("Number of questions", 3, 20, 5)
        diff = c4.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=1)
        qtype = c5.selectbox("Type", ["MCQ", "Subjective"])
        doc_id = doc_picker("Generate from document (optional)", "qg_doc", u["id"])
        go = st.form_submit_button("⚡ Generate", type="primary", width="stretch")
    if go:
        if not topic and not doc_id:
            st.error("Enter a topic or pick a document.")
        else:
            ctx = spread_context(doc_text(doc_id, u["id"])) if doc_id else ""
            with st.spinner("Generating questions…"):
                qs = safe_call(generate_questions, exam, topic or "the provided material", n, diff, qtype, ctx)
            if qs:
                st.session_state.generated = {"qs": qs, "type": qtype, "exam": exam, "topic": topic, "diff": diff}
    g = st.session_state.get("generated")
    if g:
        st.subheader(f"Generated {len(g['qs'])} {g['type']} questions")
        lines = []
        for i, q in enumerate(g["qs"], 1):
            with st.container(border=True):
                st.markdown(f"**Q{i}. {q['question']}**  \n`{q.get('topic','')}` · `{q.get('difficulty','')}`")
                lines.append(f"Q{i}. {q['question']}")
                if g["type"] == "MCQ":
                    for j, o in enumerate(q["options"]):
                        st.markdown(f"- **{'ABCD'[j]}.** {o}")
                        lines.append(f"   {'ABCD'[j]}. {o}")
                    with st.expander("Show answer & explanation"):
                        st.success(f"Answer: {'ABCD'[q['answer']]}. {q['options'][q['answer']]}")
                        st.write(q.get("explanation", ""))
                    lines.append(f"   Answer: {'ABCD'[q['answer']]} | {q.get('explanation','')}")
                else:
                    with st.expander(f"Model answer ({q.get('marks','?')} marks)"):
                        st.write(q.get("model_answer", ""))
                    lines.append(f"   Model answer: {q.get('model_answer','')}")
        b1, b2, b3 = st.columns(3)
        if b1.button("💾 Save to question bank"):
            for q in g["qs"]:
                run("INSERT INTO question_bank(user_id,exam,topic,difficulty,qtype,payload,created_at) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (u["id"], g["exam"], q.get("topic", g["topic"]), q.get("difficulty", g["diff"]),
                     g["type"], json.dumps(q), now()))
            st.success("Saved.")
        b2.download_button("⬇️ Download (.txt)", "\n".join(lines), file_name="questions.txt")
        b3.download_button("⬇️ Download (.json)", json.dumps(g["qs"], indent=2), file_name="questions.json")
        if g["type"] == "MCQ" and st.button("📝 Turn these into a mock test"):
            tid = run("INSERT INTO tests(user_id,title,exam,topic,difficulty,time_limit_min,questions,created_at) "
                      "VALUES(?,?,?,?,?,?,?,?)",
                      (u["id"], f"{g['topic'] or 'Custom'} test", g["exam"], g["topic"], g["diff"],
                       max(5, len(g["qs"]) * 2), json.dumps(g["qs"]), now()), fetch="id")
            st.session_state.active_test_id = tid
            st.success("Test created! Open the **Mock Tests** page to take it.")

    st.divider()
    st.subheader("📚 My question bank")
    bank = run("SELECT * FROM question_bank WHERE user_id=? ORDER BY id DESC LIMIT 200", (u["id"],), fetch="all")
    if not bank:
        st.caption("Empty. Save generated questions to build your bank.")
    for r in bank:
        p = json.loads(r["payload"])
        with st.expander(f"[{r['topic']}] {p['question'][:100]}"):
            st.write(p["question"])
            if r["qtype"] == "MCQ":
                for j, o in enumerate(p["options"]):
                    st.write(f"{'ABCD'[j]}. {o}")
                st.success(f"Answer: {'ABCD'[p['answer']]}")
                st.caption(p.get("explanation", ""))
            else:
                st.write(p.get("model_answer", ""))
            if st.button("Delete", key=f"qb{r['id']}"):
                run("DELETE FROM question_bank WHERE id=? AND user_id=?", (r["id"], u["id"]))
                st.rerun()


# ---------- Mock tests ---------- #
def page_tests():
    u = current_user()
    header("📝 Mock Tests", "Timed, auto-graded tests with detailed explanations.")
    active = st.session_state.get("taking")
    if active:
        take_test(active)
        return

    tab_new, tab_my, tab_res = st.tabs(["Create test", "My tests", "Results"])
    with tab_new:
        with st.form("test_form"):
            c1, c2 = st.columns(2)
            exam = c1.selectbox("Exam", EXAMS, index=EXAMS.index(u["target_exam"]) if u["target_exam"] in EXAMS else 0)
            topic = c2.text_input("Topic(s)", placeholder="Thermodynamics, Kinematics")
            c3, c4, c5 = st.columns(3)
            n = c3.slider("Questions", 5, 30, 10)
            diff = c4.selectbox("Difficulty", ["Easy", "Medium", "Hard", "Mixed"], index=1)
            tl = c5.slider("Time limit (min)", 5, 180, 20)
            doc_id = doc_picker("Base on document (optional)", "mt_doc", u["id"])
            go = st.form_submit_button("🚀 Generate & start", type="primary", width="stretch")
        if go:
            if not topic and not doc_id:
                st.error("Enter a topic or pick a document.")
            else:
                ctx = spread_context(doc_text(doc_id, u["id"])) if doc_id else ""
                with st.spinner("Building your test…"):
                    qs = safe_call(generate_questions, exam, topic or "the provided material", n, diff, "MCQ", ctx)
                if qs:
                    title = f"{topic or 'Document'} — {diff} ({len(qs)}Q)"
                    tid = run("INSERT INTO tests(user_id,title,exam,topic,difficulty,time_limit_min,questions,created_at) "
                              "VALUES(?,?,?,?,?,?,?,?)",
                              (u["id"], title, exam, topic, diff, tl, json.dumps(qs), now()), fetch="id")
                    start_test(tid)
                    st.rerun()
    with tab_my:
        tests = run("SELECT id,title,exam,difficulty,time_limit_min,created_at FROM tests "
                    "WHERE user_id=? ORDER BY id DESC", (u["id"],), fetch="all")
        if not tests:
            st.caption("No tests yet.")
        for t in tests:
            c1, c2, c3 = st.columns([5, 1, 1])
            c1.markdown(f"**{t['title']}** · {t['exam']} · ⏱ {t['time_limit_min']} min  \n<small>{t['created_at']}</small>",
                        unsafe_allow_html=True)
            if c2.button("Start", key=f"st{t['id']}"):
                start_test(t["id"])
                st.rerun()
            if c3.button("🗑️", key=f"dt{t['id']}"):
                run("DELETE FROM tests WHERE id=? AND user_id=?", (t["id"], u["id"]))
                st.rerun()
    with tab_res:
        show_results(u["id"])


def start_test(test_id):
    u = current_user()
    t = run("SELECT * FROM tests WHERE id=? AND user_id=?", (test_id, u["id"]), fetch="one")
    if t:
        t["questions"] = json.loads(t["questions"])
        t["started"] = time.time()
        st.session_state.taking = t


def take_test(t):
    u = current_user()
    elapsed = int(time.time() - t["started"])
    limit = t["time_limit_min"] * 60
    c1, c2, c3 = st.columns([3, 1, 1])
    c1.subheader(t["title"])
    c2.metric("Time limit", f"{t['time_limit_min']} min")
    remaining = limit - elapsed
    c3.metric("Remaining (at load)", f"{max(remaining, 0)//60}m {max(remaining, 0)%60}s")
    if remaining < 0:
        st.warning("⏰ Time limit exceeded — you can still submit, but it will be flagged as overtime.")
    st.caption("The timer refreshes whenever you interact with the page. Time is verified on submission.")

    with st.form("take_test"):
        answers = {}
        for i, q in enumerate(t["questions"]):
            st.markdown(f"**Q{i+1}. {q['question']}**")
            answers[i] = st.radio(
                f"q{i}", list(range(len(q["options"]))), index=None, label_visibility="collapsed",
                format_func=lambda j, q=q: f"{'ABCD'[j]}. {q['options'][j]}", key=f"tq{i}")
            st.divider()
        sub = st.form_submit_button("✅ Submit test", type="primary", width="stretch")
    if st.button("✖ Cancel test"):
        st.session_state.taking = None
        st.rerun()
    if sub:
        dur = int(time.time() - t["started"])
        score, stats, review = 0, {}, []
        for i, q in enumerate(t["questions"]):
            correct = answers[i] == q["answer"]
            score += int(correct)
            tp = q.get("topic", "General")
            s = stats.setdefault(tp, [0, 0])
            s[0] += int(correct)
            s[1] += 1
            review.append({"your": answers[i]})
        aid = run("INSERT INTO attempts(user_id,test_id,score,total,duration_sec,overtime,answers,topic_stats,created_at) "
                  "VALUES(?,?,?,?,?,?,?,?,?)",
                  (u["id"], t["id"], score, len(t["questions"]), dur, int(dur > limit),
                   json.dumps(review), json.dumps(stats), now()), fetch="id")
        st.session_state.taking = None
        st.session_state.review_attempt = aid
        st.rerun()


def show_results(uid):
    aid = st.session_state.get("review_attempt")
    att = run("SELECT a.*, t.title, t.questions FROM attempts a LEFT JOIN tests t ON t.id=a.test_id "
              "WHERE a.user_id=? ORDER BY a.id DESC", (uid,), fetch="all")
    if not att:
        st.caption("No attempts yet.")
        return
    ids = [a["id"] for a in att]
    default = ids.index(aid) if aid in ids else 0
    sel = st.selectbox("Attempt", ids, index=default,
                       format_func=lambda i: next(f"{a['title'] or 'Deleted test'} — {a['score']}/{a['total']} — {a['created_at']}"
                                                  for a in att if a["id"] == i))
    a = next(x for x in att if x["id"] == sel)
    pct = a["score"] / a["total"] * 100 if a["total"] else 0
    m1, m2, m3 = st.columns(3)
    m1.metric("Score", f"{a['score']}/{a['total']}", f"{pct:.0f}%")
    m2.metric("Time taken", f"{a['duration_sec']//60}m {a['duration_sec']%60}s")
    m3.metric("Status", "Overtime ⏰" if a["overtime"] else "On time ✅")
    if pct >= 80:
        st.balloons()
    stats = json.loads(a["topic_stats"] or "{}")
    if stats:
        sdf = pd.DataFrame([{"Topic": k, "Accuracy %": round(v[0] / v[1] * 100)} for k, v in stats.items()])
        st.bar_chart(sdf.set_index("Topic"), height=220)
    if not a["questions"]:
        return
    qs, your = json.loads(a["questions"]), json.loads(a["answers"])
    st.subheader("Review")
    for i, q in enumerate(qs):
        y = your[i]["your"] if i < len(your) else None
        ok = y == q["answer"]
        with st.expander(f"{'✅' if ok else '❌'} Q{i+1}. {q['question'][:100]}"):
            st.write(q["question"])
            for j, o in enumerate(q["options"]):
                tag = " ✅ correct" if j == q["answer"] else (" ← your answer" if j == y else "")
                st.write(f"{'ABCD'[j]}. {o}{tag}")
            if y is None:
                st.warning("Not answered")
            st.info(q.get("explanation", ""))


# ---------- Analytics ---------- #
def page_analytics():
    u = current_user()
    header("📊 Performance Analytics", "Understand strengths, weaknesses and trends.")
    att = df_query("SELECT * FROM attempts WHERE user_id=? ORDER BY id", (u["id"],))
    if att.empty:
        st.info("No data yet — take a mock test first.")
        return
    att["pct"] = (att["score"] / att["total"] * 100).round(1)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Attempts", len(att))
    c2.metric("Average", f"{att['pct'].mean():.1f}%")
    c3.metric("Best", f"{att['pct'].max():.0f}%")
    c4.metric("Avg time / test", f"{att['duration_sec'].mean()/60:.1f} min")

    st.subheader("Score trend")
    st.line_chart(att.set_index("created_at")["pct"], height=260)

    agg = {}
    for s in att["topic_stats"]:
        for k, v in json.loads(s or "{}").items():
            a = agg.setdefault(k, [0, 0])
            a[0] += v[0]
            a[1] += v[1]
    if agg:
        tdf = pd.DataFrame([{"Topic": k, "Correct": v[0], "Attempted": v[1],
                             "Accuracy %": round(v[0] / v[1] * 100, 1)} for k, v in agg.items()])
        tdf = tdf.sort_values("Accuracy %")
        l, r = st.columns(2)
        with l:
            st.subheader("Topic accuracy")
            st.bar_chart(tdf.set_index("Topic")["Accuracy %"], height=300)
        with r:
            st.subheader("Focus areas")
            st.dataframe(tdf.head(8), hide_index=True, width="stretch")
        weak = tdf[tdf["Accuracy %"] < 60]["Topic"].tolist()
        strong = tdf[tdf["Accuracy %"] >= 80]["Topic"].tolist()
        st.write(f"**Weak topics:** {', '.join(weak) or '—'}")
        st.write(f"**Strong topics:** {', '.join(strong) or '—'}")

        if st.button("🤖 Get AI insights & recommendations", type="primary"):
            summary = (f"Attempts: {len(att)}, avg {att['pct'].mean():.1f}%, last 5 scores: {att['pct'].tail(5).tolist()}. "
                       f"Topic accuracy: {dict(zip(tdf['Topic'], tdf['Accuracy %']))}. "
                       f"Target exam: {u['target_exam']}.")
            with st.spinner("Analyzing…"):
                out = safe_call(llm, [
                    {"role": "system", "content": "You are a data-driven exam coach. Be specific and concise."},
                    {"role": "user", "content": "Analyze this student's performance and give: key observations, "
                     "top 3 priorities, a 7-day improvement plan, and motivation.\n\n" + summary}],
                    temperature=0.5)
            if out:
                st.markdown(out)


# ---------- Documents ---------- #
def page_documents():
    u = current_user()
    header("📁 Study Documents", "Upload PDF / Word / text notes to use in doubts, questions and tests.")
    files = st.file_uploader("Upload files", type=["pdf", "docx", "txt", "md"], accept_multiple_files=True)
    if files and st.button("📤 Process uploads", type="primary"):
        for f in files:
            if f.size > 15 * 1024 * 1024:
                st.error(f"{f.name}: larger than 15 MB.")
                continue
            try:
                text, ftype = extract_text(f)
                text = text.strip()
                if not text:
                    st.warning(f"{f.name}: no extractable text (scanned PDF?).")
                    continue
                run("INSERT INTO documents(user_id,filename,filetype,chars,content,created_at) VALUES(?,?,?,?,?,?)",
                    (u["id"], f.name, ftype, len(text), text[:MAX_DOC_CHARS], now()))
                st.success(f"{f.name}: {len(text):,} characters extracted.")
            except Exception as e:
                st.error(f"{f.name}: {e}")
    st.subheader("Your library")
    docs = user_docs(u["id"])
    if not docs:
        st.caption("No documents yet.")
    for d in docs:
        with st.expander(f"📄 {d['filename']} — {d['chars']:,} chars — {d['created_at']}"):
            txt = doc_text(d["id"], u["id"])
            st.text_area("Preview", txt[:3000], height=160, disabled=True, key=f"pv{d['id']}")
            c1, c2 = st.columns(2)
            if c1.button("✨ Summarize", key=f"sm{d['id']}"):
                with st.spinner("Summarizing…"):
                    out = safe_call(llm, [
                        {"role": "system", "content": "You summarize study material for exam revision."},
                        {"role": "user", "content": "Create concise revision notes (headings, key points, formulas, "
                         "definitions) from:\n\n" + spread_context(txt, 14000)}], max_tokens=3000)
                if out:
                    st.markdown(out)
            if c2.button("🗑️ Delete", key=f"dd{d['id']}"):
                run("DELETE FROM documents WHERE id=? AND user_id=?", (d["id"], u["id"]))
                st.rerun()


# ---------- Profile ---------- #
def page_profile():
    u = current_user()
    header("👤 Profile", "Manage your account.")
    with st.form("prof"):
        exam = st.selectbox("Target exam", EXAMS, index=EXAMS.index(u["target_exam"]) if u["target_exam"] in EXAMS else 0)
        ok = st.form_submit_button("Save")
    if ok:
        run("UPDATE users SET target_exam=? WHERE id=?", (exam, u["id"]))
        st.session_state.user["target_exam"] = exam
        st.success("Saved.")
    st.subheader("Change password")
    with st.form("pw"):
        old = st.text_input("Current password", type="password")
        new = st.text_input("New password (min 8)", type="password")
        go = st.form_submit_button("Update password")
    if go:
        row = run("SELECT * FROM users WHERE id=?", (u["id"],), fetch="one")
        _, h = hash_pw(old, row["salt"])
        if not hmac.compare_digest(h, row["pw_hash"]):
            st.error("Current password is incorrect.")
        elif len(new) < 8:
            st.error("New password too short.")
        else:
            salt, nh = hash_pw(new)
            run("UPDATE users SET salt=?, pw_hash=? WHERE id=?", (salt, nh, u["id"]))
            st.success("Password updated.")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    init_db()
    u = current_user()
    if not u:
        auth_page()
        return

    # refresh user & ensure still active
    fresh = run("SELECT * FROM users WHERE id=?", (u["id"],), fetch="one")
    if not fresh or not fresh["active"]:
        st.session_state.clear()
        st.rerun()
    st.session_state.user = fresh

    pages = {
        "🏠 Dashboard": page_dashboard,
        "💬 Doubt Solver": page_doubts,
        "🗓️ Study Plan": page_plan,
        "🧠 Question Generator": page_questions,
        "📝 Mock Tests": page_tests,
        "📊 Analytics": page_analytics,
        "📁 Documents": page_documents,
        "👤 Profile": page_profile,
    }

    initials = "".join(p[0] for p in re.split(r"[ ._-]+", fresh["username"]) if p)[:2].upper() or "U"
    role_label = "Student"
    with st.sidebar:
        st.markdown(
            f"""
            <div class="brand"><div class="logo">🎓</div>
              <div><div class="bn">ExamPrep AI</div><div class="bs">Smart exam preparation</div></div></div>
            <div class="uchip"><div class="av">{html.escape(initials)}</div>
              <div><div class="un">{html.escape(fresh['username'])}</div>
                   <div class="ur">{role_label} · {html.escape(fresh['target_exam'] or 'No exam set')}</div></div></div>
            """,
            unsafe_allow_html=True,
        )
        choice = st.radio("Navigate", list(pages.keys()), key="nav", label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sign out", width="stretch"):
            st.session_state.clear()
            st.rerun()

    if choice != "🏠 Dashboard":
        st.button("← Back to Dashboard", key="back_dash", on_click=goto, args=("🏠 Dashboard",))
    pages[choice]()
    st.markdown(
        f'<div class="footer">© {date.today().year} ExamPrep AI · Powered by Groq · '
        "AI answers may contain errors — verify important facts.</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
