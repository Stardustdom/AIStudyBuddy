import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp {font-family: 'Inter', system-ui, sans-serif;}

/* chrome */
header[data-testid="stHeader"] {background: transparent;}
#MainMenu, footer, [data-testid="stDeployButton"], [data-testid="stToolbar"] {visibility: hidden; height: 0;}
.block-container {padding: 1.4rem 2rem 3rem; max-width: 1600px;}
.stApp {background: radial-gradient(1200px 600px at 10% -10%, rgba(99,102,241,.14), transparent 60%),
                    radial-gradient(900px 500px at 100% 0%, rgba(168,85,247,.10), transparent 55%), var(--background-color, #0b0f1a);}

/* top bar */
.sb-top {display:flex; align-items:center; gap:14px; margin: 0 0 1.1rem;}
.sb-title {font-size: 1.55rem; font-weight: 700; letter-spacing: -.02em; margin:0;
           background: linear-gradient(90deg,#c7d2fe,#a78bfa); -webkit-background-clip:text; background-clip:text; color:transparent;}
.sb-chip {font-size:.72rem; font-weight:600; padding:.28rem .65rem; border-radius:999px;
          background: rgba(129,140,248,.14); color:#a5b4fc; border:1px solid rgba(129,140,248,.28);}

/* inline-editable notebook title */
[class*="st-key-title_edit"] input {
    font-size: 1.5rem; font-weight: 700; letter-spacing: -.02em; background: transparent;
    border: 1px solid transparent; padding: .25rem .6rem; border-radius: 10px;
}
[class*="st-key-title_edit"] input:hover {border-color: rgba(148,163,184,.3);}
[class*="st-key-title_edit"] input:focus {border-color: #818cf8; background: rgba(129,140,248,.08);}

/* running-job pill */
.sb-job {display:flex; align-items:center; gap:10px; padding:.55rem .9rem; border-radius:12px;
         background: rgba(129,140,248,.14); border:1px solid rgba(129,140,248,.35);}
.sb-job-t {margin-left:auto; opacity:.7; font-size:.8rem;}
.sb-spin {width:14px; height:14px; border-radius:50%; border:2px solid rgba(129,140,248,.35); border-top-color:#818cf8;
          animation: sbspin .8s linear infinite;}
@keyframes sbspin {to {transform: rotate(360deg);}}
@media (prefers-reduced-motion: reduce) {.sb-spin {animation: none;}}
/* disabled controls look disabled */
.stButton > button:disabled, .stDownloadButton > button:disabled {opacity:.38; cursor:not-allowed; transform:none; box-shadow:none;}

/* panels */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px; border: 1px solid rgba(148,163,184,.16);
    background: rgba(19,26,43,.62); backdrop-filter: blur(6px);
}
h2, h3 {letter-spacing: -.01em;}
.stApp h3 {font-size: .78rem !important; text-transform: uppercase; letter-spacing: .12em; font-weight: 700 !important; opacity:.75; margin-bottom:.4rem;}

/* buttons */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    border-radius: 10px; font-weight: 600; border: 1px solid rgba(148,163,184,.22);
    transition: transform .12s ease, border-color .12s ease, box-shadow .12s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {transform: translateY(-1px); border-color:#818cf8; box-shadow:0 6px 18px rgba(99,102,241,.22);}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(135deg,#6366f1,#8b5cf6); border: none; color:#fff;}

/* tabs */
.stTabs [data-baseweb="tab-list"] {gap: 6px; border-bottom: 1px solid rgba(148,163,184,.14);}
.stTabs [data-baseweb="tab"] {border-radius: 10px 10px 0 0; padding: .55rem 1rem; font-weight:600;}
.stTabs [aria-selected="true"] {color:#c7d2fe;}

/* chat */
[data-testid="stChatMessage"] {border-radius: 14px; padding: .9rem 1rem; margin-bottom:.6rem;
    background: rgba(148,163,184,.07); border: 1px solid rgba(148,163,184,.10);}
[data-testid="stChatInput"] {border-radius: 14px;}

/* inputs, expanders, misc */
[data-testid="stExpander"] {border-radius: 12px; border: 1px solid rgba(148,163,184,.16); background: rgba(148,163,184,.04);}
[data-testid="stFileUploaderDropzone"] {border-radius: 12px; border: 1.5px dashed rgba(129,140,248,.45); background: rgba(129,140,248,.05);}
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {border-radius: 10px !important;}
[data-testid="stMetric"] {background: rgba(129,140,248,.10); border-radius: 14px; padding: .8rem 1rem;}
section[data-testid="stSidebar"] {border-right: 1px solid rgba(148,163,184,.14);}
section[data-testid="stSidebar"] .stButton > button {text-align:left; justify-content:flex-start;}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def topbar(nb, model: str, on_home, on_rename):
    """Header: back button, click-to-edit title, status chips."""
    c0, c1, c2 = st.columns([1.2, 5, 3.2], vertical_alignment="center")
    if c0.button("← Home", key="back_home", width="stretch", help="Back to all notebooks"):
        on_home()
    new = c1.text_input("Notebook title", value=nb["title"], key=f"title_edit_{nb['id']}",
                        label_visibility="collapsed", help="Click the title to rename")
    if new.strip() and new.strip() != nb["title"]:
        on_rename(new.strip())
    n_act = sum(1 for x in nb["sources"] if x.get("enabled", True))
    c2.markdown(
        f'<div style="text-align:right"><span class="sb-chip">{n_act}/{len(nb["sources"])} sources active</span> '
        f'<span class="sb-chip">🤖 {model}</span></div>',
        unsafe_allow_html=True,
    )
