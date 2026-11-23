import json

import streamlit as st

from studybuddy import store
from studybuddy.llm import status
from ui.home import go_home, open_notebook


def render_sidebar(nb=None):
    with st.sidebar:
        st.markdown("## 📚 AI Study Buddy")
        if nb is not None:
            if st.button("← All notebooks", width="stretch", type="primary"):
                go_home()
            st.divider()

        if nb is not None:
            with st.expander("⚙️ Current notebook"):
                st.download_button(
                    "⬇ Export (Markdown)", store.export_markdown(nb), f"{nb['title']}.md", width="stretch"
                )
                st.download_button(
                    "💾 Backup (JSON)", json.dumps(nb, ensure_ascii=False), f"{nb['title']}.json",
                    width="stretch", help="Hosted apps can reset their disk - keep a backup.",
                )
                if st.button("🗑 Delete notebook", width="stretch"):
                    store.delete(nb["id"])
                    go_home()

        with st.expander("📥 Restore backup"):
            up = st.file_uploader("Notebook .json", type=["json"], key="restore_up")
            if up and st.button("Restore", width="stretch"):
                try:
                    open_notebook(store.import_json(up.getvalue())["id"])
                except Exception as e:
                    st.error(f"Not a valid backup: {e}")

        with st.expander("🔑 Model & API keys"):
            st.caption(f"Active: **{status()}**")
            st.selectbox(
                "Provider", ["auto", "gemini", "groq", "openai", "ollama"], key="cfg_LLM_PROVIDER",
                help="auto = first key found, otherwise local Ollama",
            )
            st.text_input("Gemini API key", type="password", key="cfg_GEMINI_API_KEY",
                          help="Free at aistudio.google.com")
            st.text_input("Groq API key", type="password", key="cfg_GROQ_API_KEY", help="Free at console.groq.com")
            st.text_input("Tavily key (web discovery)", type="password", key="cfg_TAVILY_API_KEY")
            st.caption("Keys stay in this browser session only. For a permanent setup use Streamlit secrets.")
