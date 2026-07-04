import streamlit as st

from day9_pipeline.quiz_graph import quiz_graph
from day9_pipeline.retry_graph import retry_graph
from day9_pipeline.evaluator_graph import evaluation_graph

from memory.chat_history import ChatHistory

history = ChatHistory()


def save_chat():
    history.save_state(
        st.session_state.current_chat,
        {
            "messages": st.session_state.messages,
            "workspace": st.session_state.workspace
        }
    )


def render_workspace():

    if len(st.session_state.workspace) == 0:
        return

    st.header("📚 Study Workspace")

    for idx, result in enumerate(st.session_state.workspace):

        topic = result.get("topic", f"Topic {idx+1}")

        if st.button(
            f"📘 {topic}",
            use_container_width=True,
            key=f"workspace_{idx}"
        ):
            st.session_state.selected_workspace = idx
            st.rerun()