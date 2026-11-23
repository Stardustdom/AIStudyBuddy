import streamlit as st

from studybuddy import store
from ui.chat import render_chat
from ui.notes_view import render_notes
from ui.quiz_view import render_quiz
from ui.sidebar import render_sidebar
from ui.sources_panel import render_sources
from ui.studio_panel import render_studio
from ui.study_page import render_study_path

st.set_page_config(page_title="AI Study Buddy", page_icon="📚", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 2.2rem; max-width: 1500px;}
section[data-testid="stSidebar"] {min-width: 280px; max-width: 300px;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 12px;}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------ current notebook
nb = store.load(st.session_state.get("nb_id", "")) if st.session_state.get("nb_id") else None
if nb is None:
    existing = store.list_notebooks()
    if existing:
        nb = store.load(existing[0]["id"])
    else:
        nb = store.new_notebook()
        store.save(nb)
    st.session_state.nb_id = nb["id"]

render_sidebar(nb)

st.title(f"📖 {nb['title']}")

col_sources, col_main, col_studio = st.columns([1.05, 2.3, 1.15], gap="medium")

with col_sources:
    with st.container(border=True):
        render_sources(nb)

with col_main:
    tab_chat, tab_study, tab_quiz, tab_notes = st.tabs(["💬 Chat", "🎓 Study path", "🧠 Quiz", "📝 Notes"])
    with tab_chat:
        render_chat(nb)
    with tab_study:
        render_study_path(nb)
    with tab_quiz:
        render_quiz(nb)
    with tab_notes:
        render_notes(nb)

with col_studio:
    with st.container(border=True):
        render_studio(nb)
