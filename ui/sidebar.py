import json

import streamlit as st

from studybuddy import store
from studybuddy.llm import status


def _open(nb_id):
    st.session_state.nb_id = nb_id
    st.rerun()


def render_sidebar(nb):
    with st.sidebar:
        st.markdown("## 📚 AI Study Buddy")
        st.caption("Notebooks grounded in *your* sources")

        if st.button("➕ New notebook", width="stretch", type="primary"):
            fresh = store.new_notebook()
            store.save(fresh)
            _open(fresh["id"])

        st.markdown("###### Notebooks")
        for item in store.list_notebooks():
            active = item["id"] == nb["id"]
            if st.button(
                f"{'📖' if active else '📓'} {item['title'][:28]}",
                key=f"nb_{item['id']}",
                width="stretch",
                type="primary" if active else "secondary",
                help=f"{item['n_sources']} source(s)",
            ) and not active:
                _open(item["id"])

        st.divider()

        with st.expander("⚙️ Current notebook"):
            new_title = st.text_input("Title", value=nb["title"], key=f"title_{nb['id']}")
            if new_title.strip() and new_title.strip() != nb["title"]:
                nb["title"] = new_title.strip()
                store.save(nb)
                st.rerun()
            st.download_button(
                "⬇ Export (Markdown)", store.export_markdown(nb), f"{nb['title']}.md", width="stretch"
            )
            st.download_button(
                "💾 Backup (JSON)", json.dumps(nb, ensure_ascii=False), f"{nb['title']}.json",
                width="stretch", help="Hosted apps can reset their disk - keep a backup.",
            )
            if st.button("🗑 Delete notebook", width="stretch"):
                store.delete(nb["id"])
                st.session_state.pop("nb_id", None)
                st.rerun()

        with st.expander("📥 Restore backup"):
            up = st.file_uploader("Notebook .json", type=["json"], key="restore_up")
            if up and st.button("Restore", width="stretch"):
                try:
                    _open(store.import_json(up.getvalue())["id"])
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
