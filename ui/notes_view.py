import streamlit as st

from studybuddy import store


def render_notes(nb: dict):
    with st.form("add_note", clear_on_submit=True):
        title = st.text_input("Title", placeholder="Note title")
        body = st.text_area("Write a note", height=100)
        if st.form_submit_button("Add note") and body.strip():
            nb["notes"].append({"title": title.strip() or body.strip()[:40], "content": body.strip()})
            store.save(nb)
            st.rerun()

    if not nb["notes"]:
        st.info("Nothing here yet. Use **📌 Save to notes** under any answer, or pin a Studio output.")
        return
    for i, n in enumerate(list(nb["notes"])):
        with st.expander(n["title"] or f"Note {i + 1}"):
            st.markdown(n["content"])
            if st.button("🗑 Delete", key=f"dn_{nb['id']}_{i}"):
                nb["notes"].pop(i)
                store.save(nb)
                st.rerun()
