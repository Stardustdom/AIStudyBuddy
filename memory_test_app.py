import streamlit as st
import time
from memory.short_term import ShortTermMemory
from langchain_ollama import ChatOllama

# ---------------- CONFIG & CUSTOM WHATSAPP STYLING ----------------
st.set_page_config(page_title="ChatBot", layout="centered")

# Custom CSS to mimic WhatsApp UI, chat bubbles, header, and typing animation
st.markdown("""
    <style>
    [data-testid="stHeader"] {
    height: 0px !important;
    background: transparent !important;
}

/* 2. Strip padding from the root main container view */
.main .block-container {
    padding-top: 0rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 700px;
}

/* 3. Force your WhatsApp header element to flush against the top border */
.wa-header {
    display: flex;
    align-items: center;
    background-color: #f0f2f5;
    padding: 10px 16px;
    border-radius: 10px;
    
    /* Pulls it all the way up */
    margin-top: -35px !important; 
    margin-bottom: 20px;
    
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
    
    .wa-avatar {
        width: 45px;
        height: 45px;
        background-color: #00a884;
        color: white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 18px;
        margin-right: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .wa-status-container {
        display: flex;
        flex-direction: column;
    }
    
    .wa-name {
        font-size: 16px;
        font-weight: 600;
        color: #111b21;
        margin: 0;
        line-height: 1.2;
    }
    
    .wa-status {
        font-size: 13px;
        color: #00a884;
        margin: 2px 0 0 0;
        font-weight: 500;
    }
    
    /* --- BUBBLE STYLES --- */
    .chat-bubble {
        padding: 10px 14px;
        border-radius: 12px;
        max-width: 70%;
        margin: 5px 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 15px;
        line-height: 1.4;
        box-shadow: 0 1px 0.5px rgba(0,0,0,0.13);
        display: inline-block;
    }
    
    /* User Bubble (Right & Green) */
    .user-container {
        display: flex;
        justify-content: flex-end;
        width: 100%;
    }
    .user-bubble {
        background-color: #d9fdd3 !important;
        color: #111b21 !important;
        border-top-right-radius: 0px;
    }
    
    /* Assistant Bubble (Left & White) */
    .assistant-container {
        display: flex;
        justify-content: flex-start;
        width: 100%;
    }
    .assistant-bubble {
        background-color: #ffffff !important;
        color: #111b21 !important;
        border-top-left-radius: 0px;
        border: 1px solid #e9edef;
    }
    
    /* --- TYPING DOTS --- */
    .typing-dots {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 8px 10px;
    }
    .dot {
        width: 8px;
        height: 8px;
        background-color: #8696a0;
        border-radius: 50%;
        animation: pulse 1.3s infinite ease-in-out;
    }
    .dot:nth-child(2) { animation-delay: 0.2s; }
    .dot:nth-child(3) { animation-delay: 0.4s; }
    
    @keyframes pulse {
        0%, 100% { transform: scale(0.8); opacity: 0.4; }
        50% { transform: scale(1.2); opacity: 1; }
    }
    </style>
""", unsafe_allow_html=True)

# ---------------- MEMORY & INITIALIZATION ----------------
if "memory" not in st.session_state:
    st.session_state.memory = ShortTermMemory(max_len=5)

memory = st.session_state.memory

@st.cache_resource
def load_llm():
    return ChatOllama(model="mistral")

llm = load_llm()

# ---------------- WHATSAPP USER HEADER ----------------
st.markdown("""
    <div class="wa-header">
        <div class="wa-avatar">🤖</div>
        <p class="wa-name" style="margin: 0; padding-left: 2px;">Bot with Memory</p>
    </div>
""", unsafe_allow_html=True)
SYSTEM_PROMPT = """
You are a natural conversational assistant.
Rules:
- Never show reasoning or meta commentary
- Never include phrases like "the assistant recognizes"
- Reply naturally and directly
"""

def build_prompt(history, user_input):
    text = SYSTEM_PROMPT + "\n\n"
    for m in history:
        role = "User" if m["role"] == "user" else "Assistant"
        text += f"{role}: {m['content']}\n"
    text += f"User: {user_input}\nAssistant:"
    return text

# ---------------- RENDER HISTORY ----------------
for msg in memory.get():
    if msg["role"] == "user":
        st.markdown(f'<div class="user-container"><div class="chat-bubble user-bubble">{msg["content"]}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-container"><div class="chat-bubble assistant-bubble">{msg["content"]}</div></div>', unsafe_allow_html=True)

# ---------------- INPUT & PROCESSING ----------------
user_input = st.chat_input("Type message")

if user_input:
    # 1. Store and display user message instantly
    memory.add("user", user_input)
    st.markdown(f'<div class="user-container"><div class="chat-bubble user-bubble">{user_input}</div></div>', unsafe_allow_html=True)

    # 2. Show WhatsApp Typing Animation placeholder
    with st.container():
        typing_placeholder = st.empty()
        typing_placeholder.markdown(
            '<div class="assistant-container"><div class="chat-bubble assistant-bubble"><div class="typing-dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div></div></div>', 
            unsafe_allow_html=True
        )
        
        # Generate response from LLM
        prompt = build_prompt(memory.get()[:-1], user_input)
        response = llm.invoke(prompt).content
        
        # Clear the typing dots animation
        typing_placeholder.empty()

    # 3. Display the final response inside an assistant bubble
    st.markdown(f'<div class="assistant-container"><div class="chat-bubble assistant-bubble">{response}</div></div>', unsafe_allow_html=True)

    # 4. Save to memory and refresh state cleanly
    memory.add("assistant", response)
    st.rerun()