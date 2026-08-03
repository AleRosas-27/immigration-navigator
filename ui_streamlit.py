"""
Immigration Navigator — Streamlit UI
F-1 -> OPT -> STEM OPT -> H-1B RAG assistant

Run locally:
    pip install streamlit
    streamlit run ui_streamlit.py

Backend: FastAPI on port 8000
"""

import streamlit as st
import random
import re
import os
import base64
import requests
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Immigration Navigator",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design tokens (match existing palette) ───────────────────────────────────
TEAL       = "#5DCAA5"
TEAL_DARK  = "#0F6E56"
PANEL      = "#161B22"
PAGE_BG    = "#0D1117"
BUBBLE_BOT = "#222B35"
TEXT_MUTED = "#8B95A1"
TEXT_LABEL = "#6B7682"

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
/* ── Base ── */
.stApp {{ background-color: {PAGE_BG}; font-size: 14px; }}
section[data-testid="stSidebar"] {{ background-color: {PANEL}; }}
section[data-testid="stSidebar"] * {{ color: {TEXT_MUTED}; }}

/* ── Sidebar nav ── */
.nav-brand {{
    color: {TEAL}; font-size: 15px; font-weight: 600;
    letter-spacing: 0.02em; margin-bottom: 4px;
}}
.nav-label {{
    color: {TEXT_LABEL}; font-size: 11px; letter-spacing: 0.05em;
    margin: 14px 0 6px 0;
}}
.stage-active {{
    background: {TEAL_DARK}; color: #9FE1CB;
    font-size: 14px; font-weight: 500;
    padding: 8px 11px; border-radius: 6px; margin-bottom: 4px;
    display: flex; align-items: center; gap: 8px;
}}
.stage-item {{
    color: {TEXT_MUTED}; font-size: 14px;
    padding: 8px 11px; border-radius: 6px; margin-bottom: 4px;
    display: flex; align-items: center; gap: 8px;
}}

/* ── Sidebar buttons ── */
div[data-testid="stSidebar"] .stButton button {{
    background: transparent; border: none;
    color: {TEXT_MUTED}; text-align: left;
    padding: 8px 11px; font-size: 14px; font-weight: 400;
    width: 100%; border-radius: 6px; line-height: 1.5;
}}
div[data-testid="stSidebar"] .stButton button:hover {{
    background: {BUBBLE_BOT}; color: #C2CAD4;
}}

/* ── Chat bubbles ── */
.user-bubble {{
    background: {TEAL_DARK}; color: #CFEEE2;
    padding: 8px 12px; border-radius: 10px 10px 2px 10px;
    display: inline-block; max-width: 72%; float: right;
    clear: both; line-height: 1.45; font-size: 13.5px;
}}
.bot-bubble {{
    background: {BUBBLE_BOT}; color: #C2CAD4;
    padding: 8px 12px; border-radius: 10px 10px 10px 2px;
    display: inline-block; max-width: 72%; float: left;
    clear: both; line-height: 1.5; font-size: 13.5px;
}}
.cite {{ color: {TEAL}; font-weight: 600; }}

/* ── Source cards ── */
.src-card {{
    background: {PAGE_BG}; border-left: 2px solid {TEAL};
    padding: 10px 12px; border-radius: 0 4px 4px 0; margin-bottom: 8px;
}}
.src-id {{ color: {TEAL}; font-size: 11px; margin-bottom: 3px; }}
.src-desc {{ color: {TEXT_LABEL}; font-size: 11px; line-height: 1.4; }}

/* ── Expander ── */
.streamlit-expanderHeader {{
    background-color: {PANEL} !important;
    color: {TEXT_LABEL} !important;
    font-size: 11px !important;
    letter-spacing: 0.05em !important;
    border: none !important;
}}
.streamlit-expanderContent {{
    background-color: {PANEL} !important;
    border: none !important;
}}

/* ── Chat input ── */
.stChatInput textarea {{
    background: {PAGE_BG} !important;
    color: #C2CAD4 !important;
}}

/* ── Modal overlay ── */
.modal-overlay {{
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.75); z-index: 9999;
    display: flex; align-items: center; justify-content: center;
}}
.modal-box {{
    background: {PANEL}; border: 1px solid #2A3441;
    border-radius: 16px; padding: 36px 40px;
    width: 100%; max-width: 480px;
    box-shadow: 0 24px 64px rgba(0,0,0,0.5);
}}
.modal-header {{
    color: {TEAL}; font-size: 11px; font-weight: 700;
    letter-spacing: 0.12em; margin-bottom: 6px;
}}
.modal-title {{
    color: #E2E8F0; font-size: 22px; font-weight: 700;
    margin-bottom: 8px; line-height: 1.3;
}}
.modal-sub {{
    color: {TEXT_MUTED}; font-size: 13px;
    margin-bottom: 28px; line-height: 1.5;
}}
.progress-bar-bg {{
    height: 4px; background: #2A3441;
    border-radius: 2px; margin-bottom: 28px;
}}
.progress-bar-fill {{
    height: 4px; background: {TEAL};
    border-radius: 2px; transition: width 0.3s ease;
}}

/* ── Profile chip (sidebar) ── */
.profile-chip {{
    background: #1A2330; border: 1px solid #2A3441;
    border-radius: 8px; padding: 10px 12px;
    margin-bottom: 8px; font-size: 12px;
}}
.profile-chip-label {{
    color: {TEXT_LABEL}; font-size: 10px;
    letter-spacing: 0.08em; margin-bottom: 3px;
}}
.profile-chip-value {{
    color: #C2CAD4; font-size: 13px; font-weight: 500;
}}
.profile-empty {{
    color: {TEXT_LABEL}; font-style: italic;
}}

/* ── Welcome banner ── */
.welcome-banner {{
    background: linear-gradient(135deg, {TEAL_DARK}22, {TEAL}11);
    border: 1px solid {TEAL}33; border-radius: 12px;
    padding: 18px 20px; margin-bottom: 20px;
}}

/* ── Sticky footer, matched to the actual rendered DOM (stMain > 
   stMainBlockContainer > stVerticalBlock). Percentage heights cascade
   through this chain and recompute on every resize, so this holds at
   any window size without hardcoding pixels or using 100vh (which
   would overshoot past the header). margin-top:auto sits on the real
   flex item -- Streamlit's own last stElementContainer -- not on our
   nested .app-footer div, since auto-margins only work on the direct
   flex child itself. ── */
div[data-testid="stMainBlockContainer"] {{
    display: flex !important;
    flex-direction: column !important;
    min-height: 100% !important;
}}
div[data-testid="stMainBlockContainer"] > div[data-testid="stVerticalBlock"] {{
    display: flex !important;
    flex-direction: column !important;
    flex: 1 !important;
    min-height: 100% !important;
}}
div[data-testid="stMainBlockContainer"] > div[data-testid="stVerticalBlock"] > div.stElementContainer:last-child {{
    margin-top: auto !important;
}}

/* ── Page header (reusable: Sources, How This Works, etc.) ── */
.page-label {{
    color: {TEAL}; font-size: 10px; font-weight: 600;
    letter-spacing: 0.1em; margin: 4px 0 8px 0;
}}
.page-heading {{
    font-size: 32px; font-weight: 700; color: #E6E9EF;
    margin-bottom: 14px;
}}
.page-subheading {{
    font-size: 14px; color: {TEXT_MUTED}; line-height: 1.6;
    max-width: 640px; margin-bottom: 32px;
}}
.st-key-sources_page .stButton button {{
    background: transparent !important;
    border: none !important;
    color: {TEXT_MUTED} !important;
    font-size: 13px !important;
    padding: 0 !important;
    margin-bottom: 12px !important;
    height: auto !important;
}}
.st-key-sources_page .stButton button:hover {{ color: {TEAL} !important; }}

/* ── Source cards ── */
.source-card {{
    background: {BUBBLE_BOT}; border: 1px solid #2A3441;
    border-radius: 16px; padding: 22px 24px; margin-bottom: 16px;
}}
.source-card-top {{
    display: flex; justify-content: space-between; align-items: center;
}}
.source-card-title {{ font-size: 17px; font-weight: 600; color: #E6E9EF; }}
.source-card-link {{ color: {TEXT_MUTED}; text-decoration: none; font-size: 16px; }}
.source-card-link:hover {{ color: {TEAL}; }}
.source-card-desc {{
    font-size: 13px; color: {TEXT_MUTED}; line-height: 1.6; margin-top: 8px;
}}
.app-footer {{
    border-top: 1px solid #2A3441;
    padding: 28px 4px 8px 4px;
}}
.st-key-app_footer {{
    border-top: 1px solid #2A3441;
    padding-top: 28px; margin-top: 12px;
}}
.st-key-app_footer .stButton button {{
    background: transparent !important;
    border: none !important;
    color: {TEXT_LABEL} !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    padding: 0 0 10px 0 !important;
    margin: 0 !important;
    height: auto !important;
    text-align: left !important;
    justify-content: flex-start !important;
}}
.st-key-app_footer .stButton button:hover {{
    color: {TEAL} !important;
    text-decoration: underline;
}}

/* ── Team page ── */
.team-heading {{
    font-size: 28px; font-weight: 700; color: #E6E9EF;
    text-align: center; margin: 20px 0 8px 0;
}}
.team-subheading {{
    font-size: 14px; color: {TEXT_MUTED}; text-align: center;
    max-width: 560px; margin: 0 auto 40px auto; line-height: 1.6;
}}
.team-avatar-placeholder {{
    width: 120px; height: 120px; border-radius: 50%;
    background: {BUBBLE_BOT}; color: {TEAL};
    display: flex; align-items: center; justify-content: center;
    font-size: 32px; font-weight: 600;
    margin: 0 auto 12px auto;
}}
.team-avatar-photo {{
    width: 120px; height: 120px; border-radius: 50%;
    background-size: cover; background-position: center;
    margin: 0 auto 12px auto;
}}
.team-name {{ font-size: 16px; font-weight: 600; color: #E6E9EF; text-align: center; margin-top: 6px; }}
.team-role {{ font-size: 12.5px; color: {TEXT_MUTED}; text-align: center; margin-bottom: 14px; }}
.st-key-team_page [data-testid="stLinkButton"] {{ display: flex; justify-content: center; }}
.st-key-team_page [data-testid="stLinkButton"] a {{
    background: transparent !important;
    border: 1px solid {TEAL} !important;
    color: {TEAL} !important;
    border-radius: 20px !important;
    font-size: 12.5px !important;
    padding: 6px 18px !important;
    text-decoration: none !important;
}}
.st-key-team_page [data-testid="stLinkButton"] a:hover {{
    background: {TEAL} !important; color: #0D1117 !important;
}}

/* ── Top nav bar ── */
.topnav-brand {{
    color: {TEAL}; font-size: 15px; font-weight: 600;
    letter-spacing: 0.02em; display: flex; align-items: center;
    gap: 8px; height: 38px;
}}
.st-key-topnav_row {{
    border-bottom: 1px solid #2A3441;
    padding-bottom: 14px; margin-bottom: 22px;
}}
.st-key-topnav_row .stButton button {{
    background: transparent !important;
    border: none !important;
    color: {TEXT_MUTED} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    border-radius: 20px !important;
    width: 100% !important;
    transition: background 0.15s ease, color 0.15s ease;
}}
.st-key-topnav_row .stButton button:hover {{
    background: {BUBBLE_BOT} !important;
    color: #C2CAD4 !important;
}}
.topnav-item-active {{
    background: {TEAL}; color: #0D1117;
    font-size: 13px; font-weight: 600;
    padding: 8px 16px; border-radius: 20px;
    text-align: center; width: 100%; box-sizing: border-box;
}}
.footer-title {{
    color: #C2CAD4; font-size: 15px; font-weight: 600;
    margin-bottom: 10px;
}}
.footer-about {{
    color: {TEXT_MUTED}; font-size: 12.5px; line-height: 1.6;
    max-width: 340px;
}}
.footer-label {{
    color: {TEXT_LABEL}; font-size: 10px; letter-spacing: 0.08em;
    margin-bottom: 10px;
}}
.footer-item {{
    color: {TEXT_MUTED}; font-size: 12.5px; line-height: 1.9;
}}
.footer-feedback {{
    color: {TEXT_LABEL}; font-size: 12px; margin-top: 16px;
    display: inline-flex; align-items: center; gap: 6px;
}}
.footer-feedback a {{ color: {TEXT_LABEL}; text-decoration: none; }}
.footer-feedback a:hover {{ color: {TEAL}; }}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
API_URL = "http://localhost:8000/ask"

VISA_OPTIONS = [
    "F-1 Student",
    "F-1, currently on OPT",
    "F-1, on STEM OPT",
    "H-1B pending",
    "Other / Not sure",
]

EMPLOYER_OPTIONS = [
    "Full-time employer",
    "Part-time employer",
    "Multiple employers",
    "Consulting firm",
    "Self-employed",
    "Not yet employed",
]

NAV_ITEMS = ["Chat", "How This Works", "Sources", "Team"]

# Photo paths point into assets/team/ in the repo. If a file doesn't exist yet,
# the page falls back to an initials placeholder -- so this works today and
# just needs the real image files dropped in later, no code changes required.
TEAM_MEMBERS = [
    {"name": "Alejandra Rosas",  "role": "RAG Engineer",             "linkedin": "https://www.linkedin.com/in/alejandra-rosas-corral/", "photo": "assets/team/alejandra.png"},
    {"name": "Rohan Kapur",      "role": "Data Infrastructure & UI", "linkedin": "https://www.linkedin.com/in/rohan--kapur/",            "photo": "assets/team/rohan.png"},
    {"name": "Duc Nguyen",       "role": "UI / Streamlit",           "linkedin": "https://www.linkedin.com/in/ducnguyen7/",              "photo": "assets/team/duc.png"},
    {"name": "Clover Ausdemore", "role": "RAG Engineer",             "linkedin": "https://www.linkedin.com/in/ausdemore/",               "photo": "assets/team/clover.png"},
]

def _photo_data_uri(path):
    ext  = os.path.splitext(path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"

def render_team_page():
    with st.container(key="team_page"):
        st.markdown(
            "<div class='team-heading'>Hey, we're the team behind Immigration Navigator!</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='team-subheading'>This is our Summer 2026 Capstone project "
            "at the UC Berkeley MIDS program.</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(len(TEAM_MEMBERS))
        for col, member in zip(cols, TEAM_MEMBERS):
            with col:
                if os.path.exists(member["photo"]):
                    uri = _photo_data_uri(member["photo"])
                    st.markdown(
                        f"<div class='team-avatar-photo' "
                        f"style=\"background-image:url('{uri}');\"></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    initials = "".join(p[0] for p in member["name"].split()[:2]).upper()
                    st.markdown(
                        f"<div class='team-avatar-placeholder'>{initials}</div>",
                        unsafe_allow_html=True,
                    )
                st.markdown(f"<div class='team-name'>{member['name']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='team-role'>{member['role']}</div>", unsafe_allow_html=True)
                st.link_button("LinkedIn ↗", member["linkedin"], use_container_width=True)

def render_placeholder_page(title):
    st.markdown(f"<h3 style='color:{TEAL};'>{title}</h3>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:{TEXT_MUTED}; font-size:13px;'>Content coming soon.</div>",
        unsafe_allow_html=True,
    )

SOURCES_LIST = [
    {
        "name": "USCIS Policy Manual",
        "desc": "The official USCIS guidance covering F-1, OPT, STEM OPT, and H-1B "
                "eligibility, filing procedures, and status requirements.",
        "url": "https://www.uscis.gov/policy-manual",
    },
    {
        "name": "SEVP Guidance",
        "desc": "Student and Exchange Visitor Program guidance on maintaining status, "
                "school transfers, and SEVIS reporting requirements.",
        "url": "https://studyinthestates.dhs.gov/",
    },
    {
        "name": "8 CFR Regulations",
        "desc": "The federal regulations that govern nonimmigrant student and "
                "employment-based visa categories.",
        "url": "https://www.ecfr.gov/current/title-8",
    },
]

def render_sources_page():
    with st.container(key="sources_page"):
        if st.button("← Back to Chat", key="sources_back"):
            st.session_state.active_nav = "Chat"
            st.rerun()
        st.markdown('<div class="page-label">SOURCES</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-heading">Grounded in official guidance.</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-subheading">Every answer is generated only from the public '
            'documents below — no scraping, no outside data, nothing invented.</div>',
            unsafe_allow_html=True,
        )
        for src in SOURCES_LIST:
            st.markdown(
                f"""
                <div class="source-card">
                    <div class="source-card-top">
                        <div class="source-card-title">{src['name']}</div>
                        <a href="{src['url']}" target="_blank" class="source-card-link">↗</a>
                    </div>
                    <div class="source-card-desc">{src['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
DAYS   = [str(d) for d in range(1, 32)]
YEARS  = [str(y) for y in range(datetime.now().year - 1, datetime.now().year + 6)]

STAGES = {
    "F-1 Student": {
        "icon": "◈",
        "questions": [
            "What is CPT and am I eligible?",
            "How do I maintain my F-1 status?",
            "When can I apply for OPT?",
            "Can I work off-campus on an F-1 visa?",
            "What happens if I drop below full-time enrollment?",
            "How many years can I stay on an F-1 visa?",
            "What is a DSO and what do they do?",
            "Can I transfer my F-1 to another school?",
            "What is SEVIS and why does it matter?",
            "Can I travel outside the US on an F-1 visa?",
        ],
    },
    "OPT": {
        "icon": "◈",
        "questions": [
            "How many unemployment days am I allowed on OPT?",
            "When does my OPT EAD card expire?",
            "Can I change employers on OPT?",
            "When should I apply for OPT?",
            "What happens if I exceed 90 unemployment days?",
            "Can I work part-time on OPT?",
            "Do I need to report a new job to my DSO?",
            "Can I start my own business on OPT?",
            "What is post-completion OPT?",
            "How long does USCIS take to process an OPT application?",
        ],
    },
    "STEM OPT": {
        "icon": "◈",
        "questions": [
            "Do I need a new I-20 for STEM OPT?",
            "What is Form I-983 and how do I fill it out?",
            "How long is the STEM OPT extension?",
            "When should I apply for the STEM OPT extension?",
            "Does my employer need to be E-Verify registered?",
            "How many unemployment days am I allowed on STEM OPT?",
            "What qualifies as a STEM degree for STEM OPT?",
            "Can I change employers during STEM OPT?",
            "What is the annual self-evaluation requirement?",
            "Can I do STEM OPT at a startup or small company?",
        ],
    },
    "H-1B": {
        "icon": "◈",
        "questions": [
            "What is cap-gap and how does it work?",
            "When does the H-1B lottery typically open?",
            "What qualifies as a specialty occupation for H-1B?",
            "What are my options if I don't win the H-1B lottery?",
            "How long is an H-1B visa valid?",
            "Can my employer transfer my H-1B to a new job?",
            "What happens to my status during the H-1B lottery wait?",
            "How much does it cost an employer to sponsor H-1B?",
            "Can I apply for a green card while on H-1B?",
        ],
    },
}

# ── Session state init ────────────────────────────────────────────────────────
defaults = {
    "messages":       [],
    "sources":        [],
    "active_stage":   "F-1 Student",
    "active_nav":     "Chat",
    "current_chips":  random.sample(STAGES["F-1 Student"]["questions"], 3),
    # Onboarding
    "show_modal":     True,
    "modal_step":     0,      # 0-3 = questions, 4 = done
    "modal_skipped":  False,
    # Profile answers
    "prof_visa":      None,
    "prof_stem":      None,
    "prof_grad_month": None,
    "prof_grad_day":   None,
    "prof_grad_year":  None,
    "prof_employer":  None,
    # Temp selections inside modal
    "tmp_visa":       None,
    "tmp_stem":       None,
    "tmp_grad_month": None,
    "tmp_grad_day":   None,
    "tmp_grad_year":  None,
    "tmp_employer":   None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ───────────────────────────────────────────────────────────────────
def refresh_chips(stage):
    st.session_state.current_chips = random.sample(STAGES[stage]["questions"], 3)

def parse_sources(answer):
    pattern = r'\[Source:\s*([^,\]]+?)(?:,\s*([^\]]*))?\]'
    matches = re.findall(pattern, answer)
    if not matches:
        return answer, []
    seen = {}
    for label, url in matches:
        key = label.strip()
        if key not in seen:
            seen[key] = url.strip()
    sources = []
    label_to_num = {}
    for i, (label, url) in enumerate(seen.items(), start=1):
        num = f"[{i}]"
        label_to_num[label] = num
        sources.append({"id": num, "ref": label, "url": url})
    def replace_citation(match):
        label = match.group(1).strip()
        return f"<span class='cite'>{label_to_num.get(label, '')}</span>"
    cleaned = re.sub(pattern, replace_citation, answer)
    return cleaned, sources

def build_grad_date():
    m = st.session_state.prof_grad_month
    d = st.session_state.prof_grad_day
    y = st.session_state.prof_grad_year
    if m and d and y and m != "Month" and d != "Day" and y != "Year":
        try:
            month_num = MONTHS.index(m) + 1
            return f"{y}-{month_num:02d}-{int(d):02d}"
        except Exception:
            return ""
    return ""

def build_profile():
    return {
        "visa_status":     st.session_state.prof_visa or "",
        "degree_field":    st.session_state.prof_stem or "",
        "graduation_date": build_grad_date(),
        "employer_type":   st.session_state.prof_employer or "",
    }

def get_rag_response(question, profile):
    try:
        response = requests.post(
            API_URL,
            json={"question": question, "profile": profile},
            timeout=30,
        ).json()
        raw_answer = response.get("answer", "No answer returned.")
        return parse_sources(raw_answer)
    except requests.exceptions.ConnectionError:
        return (
            "⚠️ Cannot connect to the backend. "
            "Make sure the API server is running on port 8000.",
            [],
        )
    except Exception as e:
        return f"⚠️ Error: {str(e)}", []

def commit_modal_answers():
    """Copy tmp_ values → prof_ values and close modal."""
    st.session_state.prof_visa         = st.session_state.tmp_visa
    st.session_state.prof_stem         = st.session_state.tmp_stem
    st.session_state.prof_grad_month   = st.session_state.tmp_grad_month
    st.session_state.prof_grad_day     = st.session_state.tmp_grad_day
    st.session_state.prof_grad_year    = st.session_state.tmp_grad_year
    st.session_state.prof_employer     = st.session_state.tmp_employer
    st.session_state.show_modal        = False

def skip_modal():
    st.session_state.modal_skipped = True
    st.session_state.show_modal    = False

# ── Password gate ─────────────────────────────────────────────────────────────
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.text_input("Password", type="password", key="password")
        if st.session_state.get("password") == "berkeley2026":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.stop()

check_password()

# ── ONBOARDING MODAL ──────────────────────────────────────────────────────────
MODAL_STEPS = [
    {
        "kicker":   "STEP 1 OF 4",
        "title":    "What's your current visa status?",
        "sub":      "This helps us give you relevant, stage-specific guidance.",
        "key":      "tmp_visa",
        "type":     "radio",
        "options":  VISA_OPTIONS,
    },
    {
        "kicker":   "STEP 2 OF 4",
        "title":    "Is your degree STEM or non-STEM?",
        "sub":      "STEM degrees are eligible for a 24-month OPT extension.",
        "key":      "tmp_stem",
        "type":     "radio",
        "options":  ["STEM", "Non-STEM", "Not sure"],
    },
    {
        "kicker":   "STEP 3 OF 4",
        "title":    "When do you graduate?",
        "sub":      "We use this to calculate your OPT and STEM OPT deadlines.",
        "key":      "tmp_grad",
        "type":     "date_dropdowns",
    },
    {
        "kicker":   "STEP 4 OF 4",
        "title":    "What's your employment situation?",
        "sub":      "This shapes advice about employer-sponsored options like H-1B.",
        "key":      "tmp_employer",
        "type":     "radio",
        "options":  EMPLOYER_OPTIONS,
    },
]

if st.session_state.show_modal:
    step    = st.session_state.modal_step
    cfg     = MODAL_STEPS[step]
    is_last = step == len(MODAL_STEPS) - 1
    pct     = int(((step + 1) / len(MODAL_STEPS)) * 100)

    # Clean full-page modal — no CSS overlay blocking clicks
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none !important; }
    .block-container { max-width: 560px !important; padding-top: 80px !important; }
    </style>
    """, unsafe_allow_html=True)

    _, modal_col, _ = st.columns([1, 4, 1])
    with modal_col:
        # CSS: teal radio, teal next button, clean sidebar
        st.markdown(f"""
        <style>
        /* Teal radio buttons */
        div[data-testid="stRadio"] input[type="radio"] {{ accent-color: #5DCAA5; }}
        div[data-testid="stRadio"] label {{ color: #C2CAD4 !important; font-size: 15px !important; }}
        div[data-testid="stRadio"] div[role="radiogroup"] {{ gap: 10px !important; padding: 4px 0 !important; }}

        /* Next button teal */
        div[data-testid="stHorizontalBlock"] .stButton:nth-child(2) > button {{
            background: #5DCAA5 !important;
            border: none !important;
            color: #0D1117 !important;
            font-weight: 700 !important;
        }}
        div[data-testid="stHorizontalBlock"] .stButton:nth-child(2) > button:hover {{
            background: #4AB891 !important;
        }}
        div[data-testid="stHorizontalBlock"] .stButton > button {{
            background: transparent;
            border: 1px solid #2A3441;
            color: #8B95A1;
            border-radius: 8px;
        }}

        /* Date dropdowns */
        div[data-testid="stSelectbox"] > div > div {{
            background: #1A2330 !important;
            border: 1px solid #2A3441 !important;
            color: #C2CAD4 !important;
        }}

        /* Sidebar stage buttons match design */
        div[data-testid="stSidebar"] .stButton button {{
            background: transparent !important;
            border: none !important;
            color: #8B95A1 !important;
            text-align: left !important;
            padding: 8px 11px !important;
            font-size: 14px !important;
            font-weight: 400 !important;
            width: 100% !important;
            border-radius: 6px !important;
        }}
        div[data-testid="stSidebar"] .stButton button:hover {{
            background: #222B35 !important;
            color: #C2CAD4 !important;
        }}
        </style>

        <div style="
            background:#1C2333; border:1px solid #2A3441;
            border-radius:16px; padding:32px 36px 28px 36px;
            box-shadow:0 24px 64px rgba(0,0,0,0.4);
            margin-bottom:20px;
        ">
            <div style="color:#5DCAA5; font-size:11px; font-weight:700;
                        letter-spacing:0.12em; margin-bottom:10px;">
                {cfg['kicker']}
            </div>
            <div style="color:#E2E8F0; font-size:22px; font-weight:700;
                        margin-bottom:6px; line-height:1.3;">
                {cfg['title']}
            </div>
            <div style="color:#8B95A1; font-size:13px; margin-bottom:22px;">
                {cfg['sub']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Input widget renders right after the card header (visually inside it)
        if cfg["type"] == "radio":
            current = st.session_state.get(cfg["key"])
            idx = cfg["options"].index(current) if current in cfg["options"] else 0
            st.session_state[cfg["key"]] = st.radio(
                cfg["title"],
                cfg["options"],
                index=idx,
                key=f"modal_radio_{step}",
                label_visibility="collapsed",
            )

        elif cfg["type"] == "date_dropdowns":
            # Row 1: Month (full width)
            m_idx = MONTHS.index(st.session_state.tmp_grad_month) if st.session_state.tmp_grad_month in MONTHS else 0
            st.session_state.tmp_grad_month = st.selectbox("Month", MONTHS, index=m_idx, key="modal_month")
            # Row 2: Day + Year side by side
            d_col, y_col = st.columns([1, 1])
            with d_col:
                d_idx = DAYS.index(st.session_state.tmp_grad_day) if st.session_state.tmp_grad_day in DAYS else 0
                st.session_state.tmp_grad_day = st.selectbox("Day", DAYS, index=d_idx, key="modal_day")
            with y_col:
                cur_yr = str(datetime.now().year + 1)
                y_idx = YEARS.index(cur_yr) if cur_yr in YEARS else 0
                if st.session_state.tmp_grad_year in YEARS:
                    y_idx = YEARS.index(st.session_state.tmp_grad_year)
                st.session_state.tmp_grad_year = st.selectbox("Year", YEARS, index=y_idx, key="modal_year")

        # Progress bar below options
        st.markdown(f"""
        <div style="height:4px; background:#2A3441; border-radius:2px; margin:20px 0 24px 0;">
            <div style="height:4px; background:#5DCAA5; border-radius:2px; width:{pct}%;"></div>
        </div>
        """, unsafe_allow_html=True)

        # Button row 1: Back + Next
        b1, b2 = st.columns([1, 2])
        with b1:
            if step > 0:
                if st.button("← Back", use_container_width=True, key="modal_back"):
                    st.session_state.modal_step -= 1
                    st.rerun()
        with b2:
            label = "Finish ✓" if is_last else "Next →"
            if st.button(label, use_container_width=True, key="modal_next"):
                if is_last:
                    commit_modal_answers()
                else:
                    st.session_state.modal_step += 1
                st.rerun()

        # Button row 2: Skip (small text, wider button, centered)
        st.markdown("""
        <style>
        div[data-testid="stColumn"]:has(button[kind="secondary"]#modal_skip) button {
            font-size: 10px !important;
        }
        /* Target all secondary buttons in skip row by position */
        .skip-btn button {
            font-size: 8px !important;
            color: #5B6B82 !important;
            background: transparent !important;
            border: 1px solid #2A3441 !important;
            padding: 4px 12px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        _, sc, _ = st.columns([1, 2, 1])
        with sc:
            if st.button("Skip", use_container_width=True, key="modal_skip"):
                skip_modal()
                st.rerun()
        st.markdown("""
        <style>
        /* Make skip button text smaller */
        div[data-testid="stHorizontalBlock"]:last-of-type .stButton button {
            font-size: 8px !important;
            color: #5B6B82 !important;
            padding: 6px 0 !important;
        }
        </style>
        """, unsafe_allow_html=True)

    st.stop()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
if st.session_state.active_nav != "Chat":
    st.markdown(
        '<style>section[data-testid="stSidebar"] { display: none !important; }</style>',
        unsafe_allow_html=True,
    )
else:
    with st.sidebar:
        st.markdown('<div class="nav-brand">✦ Immigration Navigator</div>', unsafe_allow_html=True)
    
        # ── Profile section ──
        st.markdown('<div class="nav-label">YOUR PROFILE</div>', unsafe_allow_html=True)
    
        # Visa status
        visa_opts_full = ["— not set —"] + VISA_OPTIONS
        visa_idx = visa_opts_full.index(st.session_state.prof_visa) if st.session_state.prof_visa in visa_opts_full else 0
        selected_visa = st.selectbox("Visa status", visa_opts_full, index=visa_idx, key="sidebar_visa")
        st.session_state.prof_visa = None if selected_visa == "— not set —" else selected_visa
    
        # Degree field
        stem_opts_full = ["— not set —", "STEM", "Non-STEM", "Not sure"]
        stem_idx = stem_opts_full.index(st.session_state.prof_stem) if st.session_state.prof_stem in stem_opts_full else 0
        selected_stem = st.selectbox("Degree type", stem_opts_full, index=stem_idx, key="sidebar_stem")
        st.session_state.prof_stem = None if selected_stem == "— not set —" else selected_stem
    
        # Graduation date — two rows to avoid cramped layout
        st.caption("Graduation date")
        gc1, gc2 = st.columns(2)
        with gc1:
            m_opts = ["Month"] + MONTHS
            m_idx  = m_opts.index(st.session_state.prof_grad_month) if st.session_state.prof_grad_month in m_opts else 0
            sel_m  = st.selectbox("Month", m_opts, index=m_idx, key="sb_month", label_visibility="collapsed")
            st.session_state.prof_grad_month = None if sel_m == "Month" else sel_m
        with gc2:
            d_opts = ["Day"] + DAYS
            d_idx  = d_opts.index(st.session_state.prof_grad_day) if st.session_state.prof_grad_day in d_opts else 0
            sel_d  = st.selectbox("Day", d_opts, index=d_idx, key="sb_day", label_visibility="collapsed")
            st.session_state.prof_grad_day = None if sel_d == "Day" else sel_d
        y_opts = ["Year"] + YEARS
        y_idx  = y_opts.index(st.session_state.prof_grad_year) if st.session_state.prof_grad_year in y_opts else 0
        sel_y  = st.selectbox("Year", y_opts, index=y_idx, key="sb_year", label_visibility="collapsed")
        st.session_state.prof_grad_year = None if sel_y == "Year" else sel_y
    
        # Employer type
        emp_opts_full = ["— not set —"] + EMPLOYER_OPTIONS
        emp_idx = emp_opts_full.index(st.session_state.prof_employer) if st.session_state.prof_employer in emp_opts_full else 0
        selected_emp = st.selectbox("Employment type", emp_opts_full, index=emp_idx, key="sidebar_emp")
        st.session_state.prof_employer = None if selected_emp == "— not set —" else selected_emp
    
        # Re-open questionnaire button
        if st.button("↺ Redo questionnaire", key="reopen_modal"):
            st.session_state.show_modal  = True
            st.session_state.modal_step  = 0
            st.session_state.modal_skipped = False
            # Reset tmp fields
            for k in ["tmp_visa","tmp_stem","tmp_grad_month","tmp_grad_day","tmp_grad_year","tmp_employer"]:
                st.session_state[k] = None
            st.rerun()
    
        st.divider()
    
        # ── Stage nav ──
        st.markdown('<div class="nav-label">YOUR STAGE</div>', unsafe_allow_html=True)
        for stage, info in STAGES.items():
            is_active = st.session_state.active_stage == stage
            icon = info["icon"]
            if is_active:
                st.markdown(
                    f'<div class="stage-active">'
                    f'<span style="color:{TEAL}; font-size:10px">{icon}</span>{stage}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(f"{icon} {stage}", key=f"stage_{stage}"):
                    st.session_state.active_stage = stage
                    refresh_chips(stage)
                    st.rerun()
    
        # ── Recent chats ──
        st.markdown('<div class="nav-label">RECENT CHATS</div>', unsafe_allow_html=True)
        if st.session_state.messages:
            user_msgs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
            for msg in user_msgs[-3:]:
                short = msg[:35] + "…" if len(msg) > 35 else msg
                st.markdown(f'<div class="stage-item">· {short}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="stage-item">No recent chats yet</div>', unsafe_allow_html=True)

# ── TOP NAV ───────────────────────────────────────────────────────────────────
with st.container(key="topnav_row"):
    brand_col, items_col = st.columns([2, 3])
    with brand_col:
        st.markdown('<div class="topnav-brand">✦ Immigration Navigator</div>', unsafe_allow_html=True)
    with items_col:
        nav_cols = st.columns(len(NAV_ITEMS))
        for col, item in zip(nav_cols, NAV_ITEMS):
            with col:
                if item == st.session_state.active_nav:
                    st.markdown(f'<div class="topnav-item-active">{item}</div>', unsafe_allow_html=True)
                else:
                    if st.button(item, key=f"topnav_{item}", use_container_width=True):
                        st.session_state.active_nav = item
                        st.rerun()

# ── MAIN AREA ─────────────────────────────────────────────────────────────────
if st.session_state.active_nav == "Chat":
    chat_col, source_col = st.columns([3, 1], gap="medium")
    
    with chat_col:
        active = st.session_state.active_stage
        icon   = STAGES[active]["icon"]
        st.markdown(f"<h4 style='color:{TEAL};'>{icon} {active}</h4>", unsafe_allow_html=True)
    
        # Profile summary banner (show if at least one field is set)
        profile = build_profile()
        filled  = [v for v in profile.values() if v]
        if filled:
            parts = []
            if profile["visa_status"]:    parts.append(profile["visa_status"])
            if profile["degree_field"]:   parts.append(profile["degree_field"])
            if profile["graduation_date"]:parts.append(f"graduating {profile['graduation_date']}")
            if profile["employer_type"]:  parts.append(profile["employer_type"])
            summary = " · ".join(parts)
            st.markdown(
                f'<div class="welcome-banner" style="color:#9FE1CB; font-size:12px;">'
                f'<span style="color:{TEAL}; font-weight:600;">Your profile</span> &nbsp;{summary}'
                f'</div>',
                unsafe_allow_html=True,
            )
    
        # Chat history
        for msg in st.session_state.messages:
            cls = "user-bubble" if msg["role"] == "user" else "bot-bubble"
            st.markdown(
                f"<div style='overflow:auto; margin-bottom:10px;'>"
                f"<div class='{cls}'>{msg['content']}</div></div>",
                unsafe_allow_html=True,
            )
    
        st.markdown("<br>", unsafe_allow_html=True)
    
        # Suggested question chips
        chip_label_col, shuffle_col = st.columns([5, 1])
        with chip_label_col:
            st.caption(f"Suggested questions for {active}:")
        with shuffle_col:
            if st.button("🔀", key="shuffle", help="Show different questions"):
                refresh_chips(active)
                st.rerun()
    
        chips = st.session_state.current_chips
        cols  = st.columns(len(chips))
        clicked = None
        for col, chip in zip(cols, chips):
            if col.button(chip, use_container_width=True, key=f"chip_{chip}"):
                clicked = chip
    
        if clicked:
            st.session_state._pending = clicked
            st.rerun()
    
        # Chat input
        prompt = st.chat_input("Ask about visas, deadlines, eligibility…")
    
        if "_pending" in st.session_state:
            prompt = st.session_state.pop("_pending")
    
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            answer, sources = get_rag_response(prompt, build_profile())
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.session_state.sources = sources
            st.rerun()
    
    # ── Sources panel ─────────────────────────────────────────────────────────────
    with source_col:
        with st.expander("SOURCES", expanded=True):
            if st.session_state.sources:
                for s in st.session_state.sources:
                    url_html = (
                        f"<a href='{s['url']}' target='_blank' "
                        f"style='color:{TEAL}; font-size:10px;'>↗ View source</a>"
                        if s.get("url") else ""
                    )
                    st.markdown(
                        f"<div class='src-card'>"
                        f"<div class='src-id'>{s['id']} {s['ref']}</div>"
                        f"{url_html}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    f"<div class='src-desc'>Sources for each answer appear here, "
                    f"grounded in USCIS regulations, SEVP guidance, and the CFR.</div>",
                    unsafe_allow_html=True,
                )
elif st.session_state.active_nav == "Team":
    render_team_page()
elif st.session_state.active_nav == "How This Works":
    render_placeholder_page("How This Works")
elif st.session_state.active_nav == "Sources":
    render_sources_page()

# ── Footer ────────────────────────────────────────────────────────────────────
with st.container(key="app_footer"):
    f_about, f_sources, f_team = st.columns([2, 1, 1])

    with f_about:
        st.markdown(
            """
            <div class="footer-title">UC Berkeley MIDS Capstone — Summer 2026</div>
            <div class="footer-about">
                A RAG-powered assistant helping international students navigate the
                F-1 → OPT → STEM OPT → H-1B visa pipeline. A research preview; not
                affiliated with USCIS or SEVP.
            </div>
            <div class="footer-feedback">
                <span>✎</span>
                <a href="mailto:immigration-navigator@berkeley.edu">Give feedback</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with f_sources:
        if st.button("SOURCES", key="footer_nav_sources"):
            st.session_state.active_nav = "Sources"
            st.rerun()
        st.markdown(
            """
            <div class="footer-item">USCIS Policy Manual</div>
            <div class="footer-item">SEVP Guidance</div>
            <div class="footer-item">8 CFR Regulations</div>
            """,
            unsafe_allow_html=True,
        )

    with f_team:
        if st.button("TEAM", key="footer_nav_team"):
            st.session_state.active_nav = "Team"
            st.rerun()
        st.markdown(
            '<div class="footer-item">Rohan · Duc · Alejandra · Clover</div>',
            unsafe_allow_html=True,
        )