"""Study path tab: Planner agent -> Researcher agent (grounded in sources when available)."""
import streamlit as st

from day9_pipeline.graph import graph
from studybuddy import store
from studybuddy.studio import enabled_sources


def build_study_track(nb: dict, topic: str) -> dict:
    srcs = [{"id": s["id"], "name": s["name"], "text": s["text"]} for s in enabled_sources(nb)]
    result = graph.invoke(
        {
            "topic": topic,
            "sources": srcs,
            "subtopics": [],
            "study_notes": [],
            "quiz_questions": [],
            "user_answers": [],
            "quiz_score": None,
            "weak_topics": [],
            "retry_count": 0,
            "analysis": "",
            "suggestions": "",
        }
    )
    result.pop("sources", None)  # don't duplicate the documents inside every track
    result["grounded"] = bool(srcs)
    nb["study"].append(result)
    st.session_state[f"track_{nb['id']}"] = len(nb["study"]) - 1
    store.save(nb)
    return result


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


def render_study_path(nb: dict):
    srcs = enabled_sources(nb)
    st.markdown(
        "Agents: **Planner** splits a topic into 5 stages → **Researcher** writes notes for each stage"
        + (" **from your sources**." if srcs else " from the web / model knowledge (add sources to ground it).")
    )
    with st.form("new_track", clear_on_submit=True):
        c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
        topic = c1.text_input(
            "Topic",
            placeholder="e.g. Neural networks" if not srcs else "Focus (e.g. 'the whole document' or a chapter)",
            label_visibility="collapsed",
        )
        go = c2.form_submit_button("Build study path", width="stretch", type="primary")
    if go:
        if not topic.strip():
            st.warning("Enter a topic first.")
        else:
            with st.spinner("Planner → Researcher running…"):
                try:
                    build_study_track(nb, topic.strip())
                except Exception as e:
                    st.error(f"Could not build the study path: {e}")
                    return
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
    if st.button("🗑 Delete this study path"):
        nb["study"].pop(idx)
        store.save(nb)
        st.rerun()
