import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from day9_pipeline.state import AgentState
import streamlit as st

from ui.sidebar import render_sidebar
from ui.chat import render_chat
from ui.workspace import render_workspace

from memory.chat_history import ChatHistory

# ==========================================
# Page Config
# ==========================================

st.set_page_config(
    page_title="AI Study Buddy",
    page_icon="📚",
    layout="wide"
)

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
# Restore Saved Chat
# ==========================================

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

# ==========================================
# Sidebar
# ==========================================

render_sidebar()

# ==========================================
# Title
# ==========================================

st.title("📚 AI Study Buddy")

st.caption(
    "Learn • Revise • Practice • Chat"
)

# ==========================================
# Chat Window
# ==========================================

render_chat()

# ==========================================
# Workspace
# ==========================================

render_workspace()