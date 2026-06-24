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

# Stage definitions

STAGES = {
    "F-1 Student": {
        "icon": "◈",
        "chips": [
            "What is CPT and am I eligible?",
            "How do I maintain F-1 status?",
            "When can I apply for OPT?",
        ],
    },
    "OPT": {
        "icon": "◈",
        "chips": [
            "Unemployment days on OPT?",
            "When does my OPT EAD expire?",
            "Can I change employers on OPT?",
        ],
    },
    "STEM OPT": {
        "icon": "◈",
        "chips": [
            "Do I need a new I-20 for STEM OPT?",
            "What is Form I-983?",
            "How long is the STEM OPT extension?",
        ],
    },
    "H-1B": {
        "icon": "◈",
        "chips": [
            "What is cap-gap?",
            "When does H-1B lottery open?",
            "What is a specialty occupation?",
        ],
    },
}

import requests

API_URL = "http://54.208.227.213:8000/ask"

# Mocked RAG backend
def get_rag_response(question: str):
    response = requests.post(API_URL, json = {
        "question": question,
        "profile": {}  
    }).json()
    return response["answer"], []
    q = question.lower()
    if "i-20" in q or "stem" in q:
        return (
            "Yes — your DSO must issue a new I-20 recommending the STEM "
            "extension before you file Form I-765. <span class='cite'>[1][2]</span>",
            [
                {"id": "[1]", "ref": "8 CFR 214.2(f)(10)(ii)", "desc": "STEM OPT extension rules"},
                {"id": "[2]", "ref": "USCIS Form I-983", "desc": "Training plan instructions"},
            ],
        )
    if "unemploy" in q:
        return (
            "You are allowed 90 days of unemployment during your initial "
            "12-month OPT period. <span class='cite'>[1]</span>",
            [{"id": "[1]", "ref": "8 CFR 214.2(f)(5)(i)", "desc": "OPT unemployment limit"}],
        )
    if "cap-gap" in q or "cap gap" in q:
        return (
            "Cap-gap automatically extends your F-1 status and work "
            "authorization if a timely H-1B petition is filed before your "
            "OPT expires. <span class='cite'>[1]</span>",
            [{"id": "[1]", "ref": "8 CFR 214.2(f)(5)(vi)", "desc": "Cap-gap extension"}],
        )
    if "cpt" in q:
        return (
            "CPT (Curricular Practical Training) allows F-1 students to work "
            "off-campus in a job directly related to their major. It must be "
            "authorized by your DSO before you begin work. <span class='cite'>[1]</span>",
            [{"id": "[1]", "ref": "8 CFR 214.2(f)(10)(i)", "desc": "CPT authorization rules"}],
        )
    if "lottery" in q or "h-1b" in q or "h1b" in q:
        return (
            "The H-1B cap lottery typically opens in March each year for an "
            "October 1 start date. USCIS uses a randomized selection process "
            "when petitions exceed the annual cap of 85,000. <span class='cite'>[1]</span>",
            [{"id": "[1]", "ref": "INA § 214(g)", "desc": "H-1B numerical cap"}],
        )
    if "employer" in q:
        return (
            "Yes — you can change employers on OPT as long as the new job is "
            "directly related to your degree. You must report the change to "
            "your DSO within 10 days. <span class='cite'>[1]</span>",
            [{"id": "[1]", "ref": "SEVP Policy Guidance 0801-02", "desc": "OPT employer reporting"}],
        )
    return (
        "I can help with questions about F-1, CPT, OPT, STEM OPT, and H-1B. "
        "Try clicking a stage in the sidebar to see suggested questions.",
        [],
    )

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sources" not in st.session_state:
    st.session_state.sources = []
if "active_stage" not in st.session_state:
    st.session_state.active_stage = "F-1 Student"

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
    st.caption(f"Suggested questions for {active}:")
    chips = STAGES[active]["chips"]
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
                st.markdown(
                    f"<div class='src-card'><div class='src-id'>{s['id']} {s['ref']}</div>"
                    f"<div class='src-desc'>{s['desc']}</div></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                f"<div class='src-desc'>Sources for each answer appear here, "
                f"grounded in USCIS regulations, SEVP guidance, and the CFR.</div>",
                unsafe_allow_html=True,
            )