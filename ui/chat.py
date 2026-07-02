import streamlit as st

from day9_pipeline.graph import graph
from memory.chat_history import ChatHistory

history = ChatHistory()


# ==========================================
# Helpers: Safe Init
# ==========================================

def init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "workspace" not in st.session_state:
        st.session_state.workspace = []

    if "current_chat" not in st.session_state:
        st.session_state.current_chat = "default_chat"


# ==========================================
# Save Current Chat
# ==========================================

def save_chat():
    history.save_state(
        st.session_state.current_chat,
        {
            "messages": st.session_state.messages,
            "workspace": st.session_state.workspace
        }
    )


# ==========================================
# Study Intent Detector (Improved)
# ==========================================

def is_study_request(prompt: str) -> bool:
    prompt = prompt.lower()

    study_keywords = [
        "study", "learn", "notes", "roadmap",
        "topic", "quiz", "teach", "explain",
        "summarize", "summary", "understand"
    ]

    return any(k in prompt for k in study_keywords)


# ==========================================
# Render Chat
# ==========================================

def render_chat():

    init_state()

    # ----------------------------
    # Render old messages
    # ----------------------------
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ----------------------------
    # Input
    # ----------------------------
    prompt = st.chat_input("Ask anything...")

    if not prompt:
        return

    # ----------------------------
    # Store user message
    # ----------------------------
    user_msg = {"role": "user", "content": prompt}

    st.session_state.messages.append(user_msg)

    history.add_message(
        st.session_state.current_chat,
        "user",
        prompt
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # ============================
    # NORMAL CHAT FLOW
    # ============================
    if not is_study_request(prompt):

        reply = (
            "👋 I can help you with study-related tasks like:\n\n"
            "- Notes\n- Quizzes\n- Explanations\n- Roadmaps"
        )

        assistant_msg = {"role": "assistant", "content": reply}

        st.session_state.messages.append(assistant_msg)

        history.add_message(
            st.session_state.current_chat,
            "assistant",
            reply
        )

        with st.chat_message("assistant"):
            st.markdown(reply)

        save_chat()
        return   # IMPORTANT: stop here (no rerun spam)

    # ============================
    # STUDY FLOW
    # ============================
    with st.chat_message("assistant"):
        with st.spinner("Generating study material..."):

            result = graph.invoke({
                "topic": prompt,
                "subtopics": [],
                "study_notes": [],
                "quiz_questions": [],
                "user_answers": [],
                "quiz_score": None,
                "weak_topics": [],
                "retry_count": 0,
                "analysis": "",
                "suggestions": ""
            })

    # ----------------------------
    # Save workspace safely
    # ----------------------------
    st.session_state.workspace.append(result)

    reply = (
        f"✅ Study material for **{prompt}** is ready.\n\n"
        "Open your workspace to view it."
    )

    assistant_msg = {"role": "assistant", "content": reply}

    st.session_state.messages.append(assistant_msg)

    history.add_message(
        st.session_state.current_chat,
        "assistant",
        reply
    )

    with st.chat_message("assistant"):
        st.markdown(reply)

    save_chat()

    # ❌ IMPORTANT: removed st.rerun()