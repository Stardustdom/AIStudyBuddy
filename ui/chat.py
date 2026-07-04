import streamlit as st

from day9_pipeline.graph import graph
from day9_pipeline.intent_router import detect_intent
from day9_pipeline.context_agent import (
    answer_from_context,
    stream_answer_from_context
)

from memory.chat_history import ChatHistory

history = ChatHistory()


# ==========================================
# Helpers
# ==========================================

def init_state():

    defaults = {
        "messages": [],
        "workspace": [],
        "current_chat": "default_chat",
        "selected_workspace": None
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def save_chat():

    history.save_state(
        st.session_state.current_chat,
        {
            "messages": st.session_state.messages,
            "workspace": st.session_state.workspace
        }
    )


def assistant_reply(text):

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": text
        }
    )

    history.add_message(
        st.session_state.current_chat,
        "assistant",
        text
    )

    with st.chat_message("assistant"):
        st.markdown(text)

    save_chat()


# ==========================================
# Render Chat
# ==========================================

def render_chat():

    init_state()

    # -------------------------
    # Old Messages
    # -------------------------

    for msg in st.session_state.messages:

        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # -------------------------
    # Chat Input
    # -------------------------

    prompt = st.chat_input("Ask anything...")

    if not prompt:
        return

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    history.add_message(
        st.session_state.current_chat,
        "user",
        prompt
    )
    # Rename only if still "New Chat"
    all_chats = history.get_all_chats()

    if (
        all_chats[st.session_state.current_chat]["title"]
        == "New Chat"
    ):
        history.auto_title(
            st.session_state.current_chat,
            prompt
        )

    with st.chat_message("user"):
        st.markdown(prompt)

    # =========================
    # Detect Intent
    # =========================

    with st.spinner("Thinking..."):
        intent = detect_intent(prompt)

# ------------------------------------------
# Follow-up detection
# ------------------------------------------

    FOLLOW_UP_WORDS = [
        "example",
        "examples",
        "syntax",
        "code",
        "program",
        "sample",
        "summary",
        "summarize",
        "advantages",
        "disadvantages",
        "uses",
        "applications",
        "important points",
        "points",
        "definition",
        "diagram",
        "flowchart",
        "difference",
        "explain again",
        "more",
        "why",
        "how"
    ]

    if (
        intent == "GENERAL_CHAT"
        and len(st.session_state.workspace) > 0
    ):
        lower = prompt.lower().strip()

        if (
            lower in FOLLOW_UP_WORDS
            or len(lower.split()) <= 3
        ):
            intent = "CONTEXT_QA"

    print("Intent:", intent)

    # =====================================================
    # NEW STUDY
    # =====================================================

    if intent == "NEW_STUDY":

        with st.chat_message("assistant"):

            with st.spinner("Creating study plan..."):

                result = graph.invoke(
                    {
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
                    }
                )

        st.session_state.workspace.append(result)

        save_chat()

        assistant_reply(
            f"✅ Study material for **{prompt}** is ready."
        )

        st.rerun()

    # =====================================================
    # CONTEXT QUESTIONS
    # =====================================================

    elif intent == "CONTEXT_QA":

        if len(st.session_state.workspace) == 0:

            assistant_reply(
                "You don't have any study material yet.\n\nStart by asking me to teach a topic."
            )

            return

        idx = st.session_state.selected_workspace

        if idx is None:
            idx = len(st.session_state.workspace) - 1

        notes = st.session_state.workspace[idx]["study_notes"]

        with st.spinner("Reading your notes..."):

            placeholder = st.empty()

            full_response = ""

            for chunk in stream_answer_from_context(
                prompt,
                notes
            ):

                full_response += chunk

                placeholder.markdown(full_response + "▌")

            placeholder.markdown(full_response)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": full_response
                }
            )

            history.add_message(
                st.session_state.current_chat,
                "assistant",
                full_response
            )

            save_chat()

        return

    # =====================================================
    # QUIZ
    # =====================================================

    elif intent == "QUIZ":

        if len(st.session_state.workspace) == 0:

            assistant_reply(
                "Study a topic first before generating a quiz."
            )

            return

        idx = st.session_state.selected_workspace

        if idx is None:
            idx = len(st.session_state.workspace) - 1

        st.session_state.selected_workspace = idx

        assistant_reply(
            "📚 Opening quiz..."
        )

        st.rerun()

    # =====================================================
    # GENERAL CHAT
    # =====================================================

    else:

        assistant_reply(
            "👋 I'm your AI Study Buddy.\n\n"
            "I can help you learn new topics, explain concepts, summarize notes, and generate quizzes."
        )