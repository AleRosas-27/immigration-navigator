"""
Immigration Navigator — Streamlit demo UI
F-1 -> OPT -> STEM OPT -> H-1B RAG assistant

Run locally:
    pip install streamlit
    streamlit run app.py

Backend integration: look for "PLUG IN RAG API HERE" below.
"""

import streamlit as st

# Page config
st.set_page_config(
    page_title="Immigration Navigator",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Theme / colors
TEAL = "#5DCAA5"
TEAL_DARK = "#0F6E56"
PANEL = "#161B22"
PAGE_BG = "#0D1117"
BUBBLE_BOT = "#222B35"
TEXT_MUTED = "#8B95A1"
TEXT_LABEL = "#6B7682"

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {PAGE_BG}; }}
    section[data-testid="stSidebar"] {{ background-color: {PANEL}; }}
    section[data-testid="stSidebar"] * {{ color: {TEXT_MUTED}; }}

    .nav-brand {{ color: {TEAL}; font-size: 15px; font-weight: 600;
                  letter-spacing: 0.02em; margin-bottom: 4px; }}
    .nav-label {{ color: {TEXT_LABEL}; font-size: 11px; letter-spacing: 0.05em;
                  margin: 14px 0 6px 0; }}

    /* FIX: both active and inactive stages use identical font-size: 14px */
    .stage-active {{
        background: {TEAL_DARK}; color: #9FE1CB;
        font-size: 14px; font-weight: 500;
        padding: 8px 11px; border-radius: 6px; margin-bottom: 4px;
        cursor: default;
        display: flex; align-items: center; gap: 8px;
    }}
    .stage-item {{
        color: {TEXT_MUTED}; font-size: 14px;
        padding: 8px 11px; border-radius: 6px; margin-bottom: 4px;
        display: flex; align-items: center; gap: 8px;
    }}
    .stage-icon-active {{ color: {TEAL}; font-size: 10px; }}
    .stage-icon {{ color: {TEXT_LABEL}; font-size: 10px; }}

    /* sidebar buttons: match stage-item exactly */
    div[data-testid="stSidebar"] .stButton button {{
        background: transparent;
        border: none;
        color: {TEXT_MUTED};
        text-align: left;
        padding: 8px 11px;
        font-size: 14px;
        font-weight: 400;
        width: 100%;
        border-radius: 6px;
        line-height: 1.5;
    }}
    div[data-testid="stSidebar"] .stButton button:hover {{
        background: {BUBBLE_BOT};
        color: #C2CAD4;
    }}

    .user-bubble {{ background: {TEAL_DARK}; color: #CFEEE2; padding: 10px 14px;
                    border-radius: 12px 12px 2px 12px; display: inline-block;
                    max-width: 80%; float: right; clear: both; line-height: 1.5; }}
    .bot-bubble {{ background: {BUBBLE_BOT}; color: #C2CAD4; padding: 10px 14px;
                   border-radius: 12px 12px 12px 2px; display: inline-block;
                   max-width: 80%; float: left; clear: both; line-height: 1.6; }}
    .cite {{ color: {TEAL}; font-weight: 600; }}

    .src-card {{ background: {PAGE_BG}; border-left: 2px solid {TEAL};
                 padding: 10px 12px; border-radius: 0 4px 4px 0; margin-bottom: 8px; }}
    .src-id {{ color: {TEAL}; font-size: 11px; margin-bottom: 3px; }}
    .src-desc {{ color: {TEXT_LABEL}; font-size: 11px; line-height: 1.4; }}

    /* style the expander to match dark theme */
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

    .stChatInput textarea {{ background: {PAGE_BG} !important; color: #C2CAD4 !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

import random

# Stage definitions, 10+ questions per stage, 3 randomly shown each time
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
            "What is the difference between CPT and OPT?",
            "Do I need a new I-20 if I change my major?",
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
            "Can I travel abroad while my OPT application is pending?",
            "What is the difference between pre- and post-completion OPT?",
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
            "What happens if my STEM OPT employer loses E-Verify status?",
            "Can I apply for STEM OPT if I already used OPT at a previous school?",
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
            "What is the difference between cap-subject and cap-exempt H-1B?",
            "Can I work for multiple employers on H-1B?",
            "What happens to my status during the H-1B lottery wait?",
            "How much does it cost an employer to sponsor H-1B?",
            "Can I apply for a green card while on H-1B?",
            "What is an LCA and why does my employer need one?",
        ],
    },
}

import re
import requests

API_URL = "http://localhost:8000/ask"

def check_password():
    if "authenticated" not in st.session_state:
        st.text_input("Password", type="password", key="password")
        if st.session_state.get("password") == "berkeley2026":
            st.session_state.authenticated = True
        else:
            st.stop()

check_password()


def parse_sources(answer: str) -> tuple:
    """
    Extract [Source: label, url] citations from RAG answer text.

    The RAG prompt tells the LLM to cite every claim as:
        [Source: label, https://uscis.gov/...]

    This function:
    1. Finds all unique [Source: ...] citations in the answer
    2. Numbers them [1], [2], [3]...
    3. Replaces the long tags with short teal [1] [2] markers in the answer
    4. Returns the cleaned answer + structured source cards for the right panel
    """
    pattern = r'\[Source:\s*([^,\]]+?)(?:,\s*([^\]]*))?\]'
    matches = re.findall(pattern, answer)

    if not matches:
        return answer, []

    # Deduplicate while preserving order
    seen = {}
    for label, url in matches:
        key = label.strip()
        if key not in seen:
            seen[key] = url.strip()

    # Build numbered source cards
    sources = []
    label_to_num = {}
    for i, (label, url) in enumerate(seen.items(), start=1):
        num = f"[{i}]"
        label_to_num[label] = num
        sources.append({"id": num, "ref": label, "url": url})

    # Replace [Source: label, url] with teal inline markers [1], [2]...
    def replace_citation(match):
        label = match.group(1).strip()
        return f"<span class='cite'>{label_to_num.get(label, '')}</span>"

    cleaned = re.sub(pattern, replace_citation, answer)
    return cleaned, sources


def get_rag_response(question: str):
    """
    Call FastAPI backend and return (answer, sources).
    Sources are parsed from the answer text and shown in the right panel.
    """
    try:
        response = requests.post(
            API_URL,
            json={"question": question, "profile": {}},
            timeout=30,
        ).json()
        raw_answer = response.get("answer", "No answer returned.")
        return parse_sources(raw_answer)
    except requests.exceptions.ConnectionError:
        return (
            "⚠️ Cannot connect to the backend. "
            "Make sure API server is running on port 8000.",
            [],
        )
    except Exception as e:
        return f"⚠️ Error: {str(e)}", []

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sources" not in st.session_state:
    st.session_state.sources = []
if "active_stage" not in st.session_state:
    st.session_state.active_stage = "F-1 Student"
if "current_chips" not in st.session_state:
    st.session_state.current_chips = random.sample(
        STAGES["F-1 Student"]["questions"], 3
    )

def refresh_chips(stage: str):
    """Pick 3 new random questions for the given stage."""
    st.session_state.current_chips = random.sample(
        STAGES[stage]["questions"], 3
    )

# Sidebar
with st.sidebar:
    st.markdown('<div class="nav-brand">✦ Immigration Navigator</div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-label">YOUR STAGE</div>', unsafe_allow_html=True)

    for stage, info in STAGES.items():
        is_active = st.session_state.active_stage == stage
        icon = info['icon']
        if is_active:
            st.markdown(
                f'<div class="stage-active">'
                f'<span class="stage-icon-active">{icon}</span>{stage}'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            if st.button(f"{icon}  {stage}", key=f"stage_{stage}"):
                st.session_state.active_stage = stage
                refresh_chips(stage)
                st.rerun()

    st.markdown('<div class="nav-label">RECENT CHATS</div>', unsafe_allow_html=True)
    if st.session_state.messages:
        user_msgs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
        for msg in user_msgs[-3:]:
            short = msg[:35] + "…" if len(msg) > 35 else msg
            st.markdown(f'<div class="stage-item">· {short}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="stage-item">No recent chats yet</div>', unsafe_allow_html=True)

# Main area: chat (center) + sources (right)
chat_col, source_col = st.columns([3, 1], gap="medium")

with chat_col:
    active = st.session_state.active_stage
    icon = STAGES[active]["icon"]
    st.markdown(
        f"<h4 style='color:{TEAL};'>{icon} {active}</h4>",
        unsafe_allow_html=True,
    )

    for msg in st.session_state.messages:
        cls = "user-bubble" if msg["role"] == "user" else "bot-bubble"
        st.markdown(
            f"<div style='overflow:auto; margin-bottom:10px;'>"
            f"<div class='{cls}'>{msg['content']}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Suggested chips row with shuffle button
    chip_label_col, shuffle_col = st.columns([5, 1])
    with chip_label_col:
        st.caption(f"Suggested questions for {active}:")
    with shuffle_col:
        if st.button("🔀", key="shuffle", help="Show different questions"):
            refresh_chips(active)
            st.rerun()

    chips = st.session_state.current_chips
    cols = st.columns(len(chips))
    clicked = None
    for col, chip in zip(cols, chips):
        if col.button(chip, use_container_width=True, key=f"chip_{chip}"):
            clicked = chip
    if clicked:
        st.session_state._pending = clicked
        st.rerun()

prompt = st.chat_input("Ask about visas, deadlines, eligibility…")

if "_pending" in st.session_state:
    prompt = st.session_state.pop("_pending")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    answer, sources = get_rag_response(prompt)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.sources = sources
    st.rerun()

# Sources panel — collapsible expander
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