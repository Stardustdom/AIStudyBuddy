import streamlit as st

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import ChatOllama

from toolsCalc import calculator


# ======================================
# PAGE CONFIG
# ======================================

st.set_page_config(
    page_title="Calculator AI",
    page_icon="🎓",
    layout="wide"
)

st.title("AI Bot with Calculator")



# ======================================
# SYSTEM PROMPT
# ======================================

SYSTEM_PROMPT = """
You are AI Study Buddy.

RULES:

1. Never reveal internal reasoning.

2. Never reveal:
   - THOUGHT
   - ACTION
   - OBSERVATION
   - TOOL CALLS
   - INTERNAL STEPS

3. For mathematical calculations:
   - Use calculator tool.
   - Never calculate manually.

4. For normal conversation:
   - Respond naturally.

5. For mixed requests:
   Example:
   "Hello, what is 8*9?"

   Respond naturally:
   "Hello! 8 × 9 is 72."

6. Never mention that a tool was used.

7. Keep responses friendly and concise.
"""


# ======================================
# LOAD AGENT
# ======================================

@st.cache_resource
def load_agent():

    model = ChatOllama(
        model="llama3.1:8b",
        temperature=0
    )

    agent = create_agent(
        model=model,
        tools=[calculator],
        system_prompt=SYSTEM_PROMPT
    )

    return agent


agent = load_agent()


# ======================================
# SESSION STATE
# ======================================

if "messages" not in st.session_state:
    st.session_state.messages = []


# ======================================
# QUICK GREETING ROUTER
# ======================================

def quick_reply(text):

    cleaned = text.lower().strip()

    if cleaned in {"hi", "hello", "hey"}:
        return "Hello! How can I help you today?"

    if cleaned in {"bye", "goodbye"}:
        return "Goodbye! Have a great day!"

    if cleaned in {"thanks", "thank you"}:
        return "You're welcome!"

    if cleaned in {"ok", "okay", "cool", "sure"}:
        return "Sounds good!"

    if cleaned == "how are you":
        return "I'm doing great! How can I assist you today?"

    return None


# ======================================
# DISPLAY OLD CHAT
# ======================================

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ======================================
# USER INPUT
# ======================================

user_input = st.chat_input(
    "Ask me anything..."
)


# ======================================
# MAIN LOGIC
# ======================================

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

    bypass_response = quick_reply(user_input)

    if bypass_response:

        assistant_text = bypass_response

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

            # Extra cleanup safety

            forbidden_phrases = [
                "THOUGHT:",
                "ACTION:",
                "OBSERVATION:",
                "TOOL:",
                "TOOL CALL:",
                "I will use the calculator",
                "Using calculator",
                "Calculator tool"
            ]

            for phrase in forbidden_phrases:
                assistant_text = assistant_text.replace(
                    phrase,
                    ""
                )

            assistant_text = assistant_text.strip()

        except Exception as e:

            assistant_text = (
                f"Error: {str(e)}"
            )

    # Display assistant message

    with st.chat_message("assistant"):
        st.markdown(assistant_text)

    # Save assistant message

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_text
        }
    )