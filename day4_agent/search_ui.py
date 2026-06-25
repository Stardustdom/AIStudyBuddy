import re
import streamlit as st

from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from searchtool import web_search


# ====================================
# PAGE CONFIG
# ====================================

st.set_page_config(
    page_title="AI Search Assistant",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 AI Search Assistant")



# ====================================
# SYSTEM PROMPT
# ====================================

SYSTEM_PROMPT = """
You are a helpful AI assistant.

You have two internal behaviors:

1. Normal conversation
2. Web search when external information is required

IMPORTANT:

- Never reveal internal reasoning.
- Never mention tools.
- Never mention searches.
- Never mention modes.
- Never output JSON.
- Never output tool calls.

Respond naturally.

If web information is needed:
Use the search tool silently and give a clean answer.

If no web information is needed:
Answer normally.
"""


# ====================================
# LOAD AGENT
# ====================================

@st.cache_resource
def load_agent():

    model = ChatOllama(
        model="llama3.1:8b",
        temperature=0
    )

    agent = create_agent(
        model=model,
        tools=[web_search],
        system_prompt=SYSTEM_PROMPT
    )

    return agent


agent = load_agent()


# ====================================
# SESSION MEMORY
# ====================================

if "messages" not in st.session_state:
    st.session_state.messages = []


# ====================================
# QUICK REPLIES
# ====================================

CONVERSATIONAL_BYPASS = {
    "hello",
    "hi",
    "hey",
    "how are you",
    "how're you",
    "good morning",
    "good afternoon",
    "good evening",
    "whats up",
    "what's up",
    "yo",
    "thank you",
    "thanks",
    "no",
    "yes",
    "ok",
    "okay",
    "bye",
    "sure",
    "cool",
    "got it"
}


def quick_reply(user_input):

    cleaned_input = re.sub(
        r"[^\w\s]",
        "",
        user_input.strip().lower()
    )

    if (
        cleaned_input in CONVERSATIONAL_BYPASS
        or (
            len(cleaned_input.split()) <= 1
            and len(cleaned_input) < 4
        )
    ):

        if "thank" in cleaned_input:

            return (
                "You're very welcome! "
                "Let me know if anything else comes up."
            )

        elif cleaned_input in {
            "no",
            "bye",
            "goodbye"
        }:

            return (
                "Alright! Feel free to reach out "
                "if you need help later. Have a great day!"
            )

        elif (
            "how are you" in cleaned_input
            or "whats up" in cleaned_input
        ):

            return (
                "I'm doing great, thank you for asking! "
                "How can I assist you today?"
            )

        elif cleaned_input in {
            "sure",
            "ok",
            "okay",
            "cool",
            "got it"
        }:

            return (
                "Sounds good! Let me know whenever "
                "you're ready for the next question."
            )

        else:

            return (
                "Hello! How can I assist you today?"
            )

    return None


# ====================================
# DISPLAY CHAT HISTORY
# ====================================

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ====================================
# CHAT INPUT
# ====================================

user_input = st.chat_input(
    "Ask me anything..."
)


# ====================================
# PROCESS INPUT
# ====================================

if user_input:

    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    bypass = quick_reply(user_input)

    if bypass:

        assistant_text = bypass

    else:

        try:

            with st.spinner("Searching / Thinking..."):

                response = agent.invoke(
                    {
                        "messages":
                        st.session_state.messages
                    }
                )

            assistant_text = (
                response["messages"][-1].content
            )

            # Cleanup
            forbidden = [
                "SEARCH MODE",
                "CHAT MODE",
                "TOOL",
                "ACTION",
                "THOUGHT",
                "OBSERVATION",
                "web_search",
                "I will search",
                "Using search tool"
            ]

            for item in forbidden:
                assistant_text = assistant_text.replace(
                    item,
                    ""
                )

            assistant_text = assistant_text.strip()

        except Exception as e:

            assistant_text = (
                f"Error: {str(e)}"
            )

    with st.chat_message("assistant"):
        st.markdown(assistant_text)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_text
        }
    )