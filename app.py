import streamlit as st

from studybuddy import store
from studybuddy.llm import status
from ui.style import inject, topbar
from ui.chat import render_chat
from ui.home import render_home
from ui.notes_view import render_notes
from ui.quiz_view import render_quiz
from ui.sidebar import render_sidebar
from ui.sources_panel import render_sources
from ui.studio_panel import render_studio
from ui.study_page import render_study_path

st.set_page_config(page_title="AI Study Buddy", page_icon="📚", layout="wide")

inject()

# ----------------------------------------------------------------- routing
# Home page (notebook list) <-> notebook view. ?nb=<id> keeps the notebook open on refresh.
if "nb_id" not in st.session_state and st.query_params.get("nb"):
    st.session_state.nb_id = st.query_params["nb"]

nb = store.load(st.session_state["nb_id"]) if st.session_state.get("nb_id") else None
if st.session_state.get("nb_id") and nb is None:  # deleted / unknown id
    st.session_state.pop("nb_id", None)
    st.query_params.clear()

render_sidebar(nb)

if nb is None:
    render_home()
    st.stop()

topbar(nb["title"], len(nb["sources"]), sum(1 for x in nb["sources"] if x.get("enabled", True)), status())

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
