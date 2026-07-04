import streamlit as st

from ui.sidebar import render_sidebar
from ui.chat import render_chat
from ui.study_page import render_study_page

from memory.chat_history import ChatHistory

# ==========================================
# Page Config
# ==========================================

st.set_page_config(
    page_title="AI Study Buddy",
    page_icon="📚",
    layout="wide"
)
st.markdown("""
<style>
section[data-testid="stSidebar"]{
    min-width: 360px;
    max-width: 360px;
}
</style>
""", unsafe_allow_html=True)
# ==========================================
# Initialize Chat History
# ==========================================

history = ChatHistory()

# ==========================================
# Session State
# ==========================================

DEFAULTS = {
    "current_chat": None,
    "messages": [],
    "workspace": [],
    "selected_workspace": None,
    "loaded_chat": None
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ==========================================
# First Chat
# ==========================================

if st.session_state.current_chat is None:

    chats = history.get_all_chats()

    if chats:
        st.session_state.current_chat = list(chats.keys())[0]
    else:
        st.session_state.current_chat = history.create_chat()

# ==========================================
# Restore Chat
# ==========================================

# ==========================================
# Restore Chat
# ==========================================

if (
    "loaded_chat" not in st.session_state
    or st.session_state.loaded_chat != st.session_state.current_chat
):

    saved = history.load_state(
        st.session_state.current_chat
    )

    if saved:

        st.session_state.messages = saved.get(
            "messages",
            []
        )

        st.session_state.workspace = saved.get(
            "workspace",
            []
        )

    else:

        st.session_state.messages = history.get_messages(
            st.session_state.current_chat
        )

        st.session_state.workspace = []

    st.session_state.loaded_chat = (
        st.session_state.current_chat
    )

# ==========================================
# Sidebar
# ==========================================

render_sidebar()

# ==========================================
# Main Area
# ==========================================

if st.session_state.selected_workspace is None:

    st.title("AI Study Buddy")

   

    render_chat()

else:

    render_study_page()