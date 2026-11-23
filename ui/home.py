from datetime import datetime

import streamlit as st

from studybuddy import store
from studybuddy.llm import status

EMOJIS = ["📘", "🧬", "🧠", "🔭", "📐", "🏛️", "💡", "🌍", "⚗️", "📊", "🎨", "⚖️"]


def emoji_for(nb_id: str) -> str:
    return EMOJIS[sum(map(ord, nb_id)) % len(EMOJIS)]


def pretty(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts).strftime("%b %d, %Y")
    except Exception:
        return ""


def open_notebook(nb_id: str):
    st.session_state.nb_id = nb_id
    st.query_params["nb"] = nb_id
    st.rerun()


def go_home():
    st.session_state.pop("nb_id", None)
    st.query_params.clear()
    st.rerun()


@st.dialog("Rename notebook")
def _rename(item):
    new = st.text_input("Title", value=item["title"])
    c1, c2 = st.columns(2)
    if c1.button("Save", type="primary", width="stretch") and new.strip():
        nb = store.load(item["id"])
        nb["title"] = new.strip()
        store.save(nb)
        st.rerun()
    if c2.button("Cancel", width="stretch"):
        st.rerun()


@st.dialog("Delete notebook?")
def _delete(item):
    st.write(f"**{item['title']}** and all its sources, chat and notes will be permanently deleted.")
    c1, c2 = st.columns(2)
    if c1.button("Delete", type="primary", width="stretch"):
        store.delete(item["id"])
        st.rerun()
    if c2.button("Cancel", width="stretch"):
        st.rerun()


def _card(item, list_view=False):
    with st.container(border=True):
        top, menu = st.columns([6, 1], vertical_alignment="center")
        top.markdown(f"<div style='font-size:2rem;line-height:1'>{emoji_for(item['id'])}</div>", unsafe_allow_html=True)
        with menu.popover("⋮"):
            if st.button("✏️ Rename", key=f"rn_{item['id']}", width="stretch"):
                _rename(item)
            if st.button("🗑 Delete", key=f"dl_{item['id']}", width="stretch"):
                _delete(item)
        if st.button(item["title"][:60], key=f"tt_{item['id']}", type="tertiary", help="Click to rename"):
            _rename(item)
        st.caption(f"{pretty(item['modified'])} · {item['n_sources']} source{'s' if item['n_sources'] != 1 else ''}")
        if st.button("Open", key=f"op_{item['id']}", width="stretch", type="secondary"):
            open_notebook(item["id"])


def render_home():
    st.markdown(
        f'<div class="sb-top"><h1 class="sb-title">📚 AI Study Buddy</h1>'
        f'<span class="sb-chip">🤖 {status()}</span></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([3, 1.4, 1.2], vertical_alignment="bottom")
    q = c1.text_input("Search notebooks", placeholder="🔍  Search by title", label_visibility="collapsed")
    sort = c2.selectbox("Sort", ["Most recent", "Title A–Z"], label_visibility="collapsed")
    view = c3.segmented_control("View", ["Grid", "List"], default="Grid", label_visibility="collapsed") or "Grid"

    items = store.list_notebooks()
    if q:
        items = [i for i in items if q.lower() in i["title"].lower()]
    if sort == "Title A–Z":
        items = sorted(items, key=lambda i: i["title"].lower())

    st.markdown("### Notebooks")
    cols_n = 1 if view == "List" else 4
    cells = [None] + items  # first cell = "create new"
    for row in range(0, len(cells), cols_n):
        cols = st.columns(cols_n)
        for col, item in zip(cols, cells[row:row + cols_n]):
            with col:
                if item is None:
                    with st.container(border=True):
                        st.markdown("<div style='font-size:2rem;line-height:1'>➕</div>", unsafe_allow_html=True)
                        st.markdown("**Create new notebook**")
                        st.caption("Start with your own sources")
                        if st.button("Create", key="create_nb", type="primary", width="stretch"):
                            fresh = store.new_notebook()
                            store.save(fresh)
                            open_notebook(fresh["id"])
                else:
                    _card(item, view == "List")
    if not items and not q:
        st.info("No notebooks yet — create your first one above.")
    elif not items:
        st.caption("No notebooks match your search.")
