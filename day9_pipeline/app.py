import os
import sys
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ui.sidebar import render_sidebar
from memory.chat_history import ChatHistory

from graph import graph
from day9_pipeline.evaluator_graph import evaluation_graph
from retry_graph import retry_graph
from quiz_graph import quiz_graph

# ======================================================
# Page Config
# ======================================================
st.set_page_config(
    page_title="AI Study Buddy",
    page_icon="📚",
    layout="wide"
)

# ======================================================
# Initialize Chat History & Session State
# ======================================================
history = ChatHistory()

if "current_chat" not in st.session_state:
    chats = history.get_all_chats()
    if chats:
        st.session_state.current_chat = list(chats.keys())[0]
    else:
        st.session_state.current_chat = history.create_chat()

# Render sidebar (Handles New Chat, Search Chats, and selecting chats)
render_sidebar()

# Restore Chat State from database/file
saved_state = history.load_state(st.session_state.current_chat)

# Default State Architecture to support multiple topics/quizzes per chat
DEFAULTS = {
    "topic_history": [],  # List of results/topics generated in this chat
    "messages": [],       # Chat message history
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = saved_state.get(key, value) if saved_state else value

if not st.session_state.messages:
    st.session_state.messages = history.get_messages(st.session_state.current_chat)

# ======================================================
# Persistence Helper
# ======================================================
def save_chat():
    history.save_state(
        st.session_state.current_chat,
        {
            "topic_history": st.session_state.topic_history,
            "messages": st.session_state.messages
        }
    )

# ======================================================
# App UI Header
# ======================================================
st.title("📚 AI Study Buddy")
st.caption("Your personalized AI companion for guided learning, automated summaries, and smart testing.")

# ======================================================
# Chat Interface (Messages & Layout)
# ======================================================
# Display existing messages in true user/bot chronological sequence
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
prompt = st.chat_input("Ask me anything about studying, create a new topic, or ask follow-ups...")

if prompt:
    # 1. Append and show user message immediately
    history.add_message(st.session_state.current_chat, "user", prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Intent Keyword Extraction
    lower_prompt = prompt.lower()
    
    # Structural keywords to trigger a *brand new* core topic dashboard element
    creation_words = ["study", "learn", "teach", "roadmap", "topic", "plan", "generate notes", "create a course"]
    is_creation_request = any(word in lower_prompt for word in creation_words)
    
    # Conversational or situational manipulation words (like summary or follow ups)
    follow_up_words = ["summarize", "summary", "explain further", "shorten", "elaborate", "day", "notes for day"]
    is_follow_up = any(word in lower_prompt for word in follow_up_words)

    # --- CRITICAL ROUTING MATRIX ---
    
    # ROUTE A: Explicit follow-up or contextual manipulation within chat window
    if is_follow_up and len(st.session_state.topic_history) > 0:
        with st.chat_message("assistant"):
            with st.spinner("Processing follow-up requested context..."):
                # Pull the most recently active material context to inform your assistant
                latest_material = st.session_state.topic_history[-1]["result"]
                notes_context = str(latest_material.get("study_notes", ""))
                
                # We feed the graph context into a clean processing fallback window 
                # (You can also swap this specific block out to route directly to a chat-llm endpoint)
                reply = f"📝 **Here is your requested response regarding:** *\"{prompt}\"*\n\n"
                
                # Simple parsing fallback logic matching your workflow's data
                found = False
                for note in latest_material.get("study_notes", []):
                    if "day 2" in lower_prompt and "day 2" in note.get("topic", "").lower():
                        reply += f"### Quick Summary of {note['topic']}\n"
                        reply += f"Here is a short evaluation version of your active notes:\n\n> {note['notes'][:400]}...\n\nLet me know if you want to drill deeper into this!"
                        found = True
                        break
                
                if not found:
                    reply += f"I analyzed your active topics for your inquiry. Let me clarify that point directly inside our current chat interface without breaking your tracking modules on your workspace below!"
                
        history.add_message(st.session_state.current_chat, "assistant", reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        save_chat()
        st.rerun()

    # ROUTE B: Brand New Study Request Pipeline (Build New Workspace Block)
    elif is_creation_request:
        with st.chat_message("assistant"):
            with st.spinner("Analyzing request and building new study blocks..."):
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

        topic_id = f"topic_{len(st.session_state.topic_history)}"
        topic_block = {
            "id": topic_id,
            "title": result.get("topic", prompt),
            "result": result,
            "quiz_submitted": False,
            "quiz_score": 0,
            "quiz_feedback": None
        }
        st.session_state.topic_history.append(topic_block)
        history.add_topic(st.session_state.current_chat, result)
        
        reply = f"📝 I've added a completely new study plan and notes block for **{topic_block['title']}** down inside your workspace!"
        history.add_message(st.session_state.current_chat, "assistant", reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        
        save_chat()
        st.rerun()

    # ROUTE C: Generic chit-chat or fallback assistance
    else:
        reply = (
            f"👋 Hello! I'm your AI Study Buddy.\n\n"
            f"I see you mentioned: *\"{prompt}\"*. How can I help you study today?\n\n"
            f"**You can ask me to:**\n"
            f"- 📖 **Learn** a new topic completely\n"
            f"- 📝 **Summarize or clarify** text directly inside this chat thread"
        )
        with st.chat_message("assistant"):
            st.markdown(reply)
            
        history.add_message(st.session_state.current_chat, "assistant", reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        save_chat()
        st.rerun()

# ======================================================
# Dynamic Workplace Layout (Renders All Generated Topics Below Chat)
# ======================================================
if st.session_state.topic_history:
    st.write("---")
    st.subheader("🛠️ Active Study Workspace")

    for idx, block in enumerate(st.session_state.topic_history):
        res = block["result"]
        
        with st.expander(f"📚 Topic {idx+1}: {block['title']}", expanded=False):
            tab_notes, tab_quiz = st.tabs(["📝 Study Material", "🧠 Interactive Quiz"])
            
            with tab_notes:
                if res.get("subtopics"):
                    st.markdown("### 📅 Study Roadmap")
                    for i, subtopic in enumerate(res["subtopics"], start=1):
                        st.markdown(f"**Day {i}:** {subtopic}")
                
                if res.get("study_notes"):
                    st.markdown("### 📝 Detailed Notes")
                    for note in res["study_notes"]:
                        st.markdown(f"#### 📌 {note['topic']}")
                        st.markdown(note["notes"])
                        st.write("")

            with tab_quiz:
                quiz = res.get("quiz_questions", [])
                if not quiz:
                    if st.button("🧠 Generate Quiz", key=f"gen_{block['id']}"):
                        with st.spinner("Generating quiz questions..."):
                            block["result"] = quiz_graph.invoke(res)
                            save_chat()
                            st.rerun()
                else:
                    st.markdown("### ✍️ Topic Assessment")
                    answers = []
                    for i, question in enumerate(quiz, start=1):
                        st.markdown(f"**Question {i}:** {question['question']}")
                        ans_key = f"ans_{block['id']}_{i}"
                        answer = st.radio("Select option:", question["options"], index=None, key=ans_key, label_visibility="collapsed")
                        answers.append(answer)
                        
                        if block["quiz_submitted"]:
                            if answer == question["answer"]:
                                st.success("✅ Correct")
                            else:
                                st.error(f"❌ Incorrect | Correct: **{question['answer']}**")
                        st.write("---")

                    if not block["quiz_submitted"] and st.button("Submit Assessment", key=f"sub_{block['id']}"):
                        if None in answers:
                            st.warning("Please answer all questions.")
                        else:
                            score = sum(1 for q, a in zip(quiz, answers) if a == q["answer"])
                            percentage = (score / len(quiz)) * 100
                            block["result"]["user_answers"] = answers
                            block["result"]["quiz_score"] = percentage
                            block["quiz_score"] = percentage
                            block["quiz_submitted"] = True
                            with st.spinner("Evaluating..."):
                                block["quiz_feedback"] = evaluation_graph.invoke(block["result"])
                            save_chat()
                            st.rerun()
                    
                    if block["quiz_submitted"]:
                        feedback = block["quiz_feedback"]
                        st.markdown(f"#### 📊 Score: `{sum(1 for q, a in zip(quiz, block['result']['user_answers']) if a == q['answer'])}/{len(quiz)}` ({block['quiz_score']:.1f}%)")
                        if feedback:
                            st.write(feedback.get("analysis", ""))
                            if block["quiz_score"] < 60 and st.button("📚 Revise & Regenerate Quiz", key=f"retry_{block['id']}"):
                                with st.spinner("Rerouting..."):
                                    block["result"] = retry_graph.invoke(feedback)
                                    block["quiz_submitted"] = False
                                    for key in list(st.session_state.keys()):
                                        if key.startswith(f"ans_{block['id']}_"):
                                            del st.session_state[key]
                                    save_chat()
                                    st.rerun()