import re
import streamlit as st

from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage

from searchtool import web_search
from toolsCalc import calculator


# ==========================================
# PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="AI Buddy",
    page_icon="🎓",
    layout="wide"
)

st.title("AI Buddy")
st.caption("Calculator + Search Tools")



# ==========================================
# SYSTEM PROMPT
# ==========================================

SYSTEM_PROMPT = """
You are a helpful, direct AI Study Buddy with access to tools.

CRITICAL TOOL RULES:

1. CALCULATOR TOOL:
- Use ONLY when there is a mathematical expression.
- Never calculate manually.

2. WEB SEARCH TOOL:
- Use ONLY when external information is required.
- Examples:
  - latest news
  - tutorials
  - websites
  - current events
  - factual lookups

3. CHAT MODE:
- If no tool is needed, respond naturally.

CRITICAL RULES:

- Never reveal internal reasoning.
- Never reveal tools.
- Never reveal tool calls.
- Never reveal chain of thought.
- Never mention:
  - calculator
  - web_search
  - action
  - thought
  - observation
  - mode

If user combines conversation and a tool request:

Example:
"Hello, what is 8*9?"

Respond naturally:

"Hello! 8 × 9 is 72."

Do not explain how you got the answer.
"""


# ==========================================
# LOAD AGENT
# ==========================================

@st.cache_resource
def load_agent():

    model = ChatOllama(
        model="llama3.1:8b",
        temperature=0
    )

    agent = create_agent(
        model=model,
        tools=[web_search, calculator],
        system_prompt=SYSTEM_PROMPT
    )

    return agent


agent = load_agent()


# ==========================================
# SESSION MEMORY
# ==========================================

if "messages" not in st.session_state:
    st.session_state.messages = []


# ==========================================
# GREETING BYPASS
# ==========================================

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
                "You're very welcome! Let me know if anything else comes up."
            )

        elif cleaned_input in {
            "no",
            "bye",
            "goodbye"
        }:

            return (
                "Alright! Feel free to reach out if you need help later. Have a great day!"
            )

        elif (
            "how are you" in cleaned_input
            or "whats up" in cleaned_input
        ):

            return (
                "I'm doing great, thank you for asking! How can I assist you today?"
            )

        elif cleaned_input in {
            "sure",
            "ok",
            "okay",
            "cool",
            "got it"
        }:

            return (
                "Sounds good! Let me know whenever you're ready for the next question."
            )

        else:

            return (
                "Hello! How can I assist you today?"
            )

    return None


# ==========================================
# DISPLAY HISTORY
# ==========================================

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ==========================================
# CHAT INPUT
# ==========================================

user_input = st.chat_input(
    "Ask me anything..."
)


# ==========================================
# PROCESS INPUT
# ==========================================

if user_input:

    # Show user message

    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    # Quick bypass

    bypass = quick_reply(user_input)

    if bypass:

        assistant_text = bypass

    else:

        history = []

        for msg in st.session_state.messages:

            if msg["role"] == "user":

                history.append(
                    HumanMessage(
                        content=msg["content"]
                    )
                )

            else:

                history.append(
                    AIMessage(
                        content=msg["content"]
                    )
                )

        try:

            with st.spinner("Thinking..."):

                response = agent.invoke(
                    {
                        "messages": history
                    }
                )

            assistant_text = (
                response["messages"][-1].content
            )

            # Cleanup Safety Layer

            forbidden_phrases = [
                "THOUGHT:",
                "ACTION:",
                "OBSERVATION:",
                "SEARCH MODE",
                "CHAT MODE",
                "CALCULATOR TOOL",
                "WEB SEARCH TOOL",
                "calculator",
                "web_search",
                "Based on the search results,",
                "According to the web search,",
                "The result of the calculation is",
                "No calculation is required"
            ]

            for phrase in forbidden_phrases:
                assistant_text = assistant_text.replace(
                    phrase,
                    ""
                )

            assistant_text = assistant_text.strip()

        except Exception as e:

            assistant_text = f"Error: {e}"

    # Display Assistant Message

    with st.chat_message("assistant"):
        st.markdown(assistant_text)

    # Save Assistant Message

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_text
        }
    )