"""Study path tab: Planner agent -> Researcher agent (grounded in sources when available).

Building a path runs as a background job (one at a time per notebook; see ui/jobs_ui.py)."""
import streamlit as st

from api import jobs
from studybuddy.studio import enabled_sources
from ui.jobs_ui import lock_hint, start


def pick_track(nb: dict, label: str, key: str):
    """Selectbox over study tracks. Returns index or None."""
    if not nb["study"]:
        return None
    default = min(st.session_state.get(f"track_{nb['id']}", len(nb["study"]) - 1), len(nb["study"]) - 1)
    idx = st.selectbox(
        label,
        range(len(nb["study"])),
        index=default,
        format_func=lambda i: nb["study"][i].get("topic", f"Topic {i + 1}")[:70],
        key=f"{key}_{nb['id']}_{len(nb['study'])}",
    )
    st.session_state[f"track_{nb['id']}"] = idx
    return idx


def render_study_path(nb: dict, locked: bool = False):
    srcs = enabled_sources(nb)
    st.markdown(
        "Agents: **Planner** splits a topic into 5 stages → **Researcher** writes notes for each stage"
        + (" **from your sources**." if srcs else " from the web / model knowledge (add sources to ground it).")
    )
    if locked:
        st.caption("⏳ " + (lock_hint(nb) or "A job is running."))
    with st.form("new_track", clear_on_submit=True):
        c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
        topic = c1.text_input(
            "Topic",
            placeholder="e.g. Neural networks" if not srcs else "Focus (e.g. 'the whole document' or a chapter)",
            label_visibility="collapsed",
            disabled=locked,
        )
        go = c2.form_submit_button("Build study path", width="stretch", type="primary", disabled=locked)
    if go:
        if not topic.strip():
            st.warning("Enter a topic first.")
        elif start(nb, "study_path", {"topic": topic.strip()}):
            st.rerun()

    idx = pick_track(nb, "Study path", "track_sel")
    if idx is None:
        st.info("No study paths yet. Enter a topic above.")
        return
    track = nb["study"][idx]
    if track.get("grounded"):
        st.caption("📎 Built from your sources")
    for i, sub in enumerate(track.get("subtopics", []), 1):
        note = next((n for n in track.get("study_notes", []) if n["topic"] == sub), None)
        with st.expander(f"Day {i} · {sub}", expanded=(i == 1)):
            if note:
                st.markdown(note["notes"])
                if note.get("from_sources"):
                    st.caption("From: " + ", ".join(note["from_sources"]))
    if st.button("🗑 Delete this study path", disabled=locked):
        with jobs.edit(nb["id"]) as n:
            n["study"] = [t for t in n["study"] if t.get("id") != track.get("id")]
        st.rerun()
