import os

import streamlit as st

from api import jobs
from studybuddy import store
from studybuddy.studio import STUDIO, enabled_sources, mindmap_dot
from ui.jobs_ui import lock_hint, start


def _audio_path(nb_id, oid):
    return os.path.join(store.DIR, "..", "audio", nb_id, f"{oid}.mp3")


def _flashcards(nb, out, key):
    cards = out["cards"]
    if not cards:
        st.warning("No cards were generated.")
        return
    i_key, f_key = f"fc_i_{key}", f"fc_flip_{key}"
    i = st.session_state.get(i_key, 0) % len(cards)
    flipped = st.session_state.get(f_key, False)
    card = cards[i]
    with st.container(border=True):
        st.caption(f"Card {i + 1} / {len(cards)}")
        st.markdown(f"### {card['back'] if flipped else card['front']}")
    c1, c2, c3 = st.columns(3)
    if c1.button("◀", key=f"{i_key}_p", width="stretch"):
        st.session_state[i_key], st.session_state[f_key] = (i - 1) % len(cards), False
        st.rerun()
    if c2.button("Flip", key=f"{f_key}_b", width="stretch"):
        st.session_state[f_key] = not flipped
        st.rerun()
    if c3.button("▶", key=f"{i_key}_n", width="stretch"):
        st.session_state[i_key], st.session_state[f_key] = (i + 1) % len(cards), False
        st.rerun()


def _render_output(nb, oid, out, locked):
    kind = out.get("kind", oid)
    key = f"{nb['id']}_{oid}"
    if kind == "flashcards":
        _flashcards(nb, out, key)
    elif kind == "mindmap":
        st.graphviz_chart(mindmap_dot(out["tree"]), width="stretch")
    elif kind == "audio":
        st.markdown(out["markdown"])
        path = _audio_path(nb["id"], oid)
        if out.get("audio_ready") and os.path.exists(path):
            st.audio(path, format="audio/mp3")
        elif st.button("🔊 Generate audio", key=f"tts_{key}", disabled=locked,
                       help=lock_hint(nb) or "Voices the script with two accents (gTTS, needs internet)"):
            if start(nb, "audio_render", {"output_id": oid}):
                st.rerun()
    else:
        st.markdown(out["markdown"])

    if out.get("markdown"):
        c1, c2 = st.columns(2)
        c1.download_button("⬇ .md", out["markdown"], f"{out['title']}.md", key=f"dl_{key}", width="stretch")
        if c2.button("📌 To notes", key=f"pin_{key}", width="stretch"):
            with jobs.edit(nb["id"]) as n:  # serialised: a running job may commit at the same time
                n["notes"].append({"title": out["title"], "content": out["markdown"]})
            st.toast("Saved to Notes 📌")


def render_studio(nb, locked=False):
    st.subheader("Studio")
    srcs = enabled_sources(nb)
    if not srcs:
        st.caption("Enable at least one source to unlock the Studio.")
    elif locked:
        st.caption("⏳ " + (lock_hint(nb) or "A job is running."))

    with st.popover("⚙ Options", disabled=locked, width="stretch"):
        st.text_input("Focus on (optional)", key="opt_focus", placeholder="e.g. chapter 3, the key formulas")
        st.selectbox("Length", ["default", "short", "long"], key="opt_length")
        st.number_input("Flashcards", 4, 40, 12, key="opt_count")
        st.text_input("Language (optional)", key="opt_language", placeholder="e.g. Hindi")

    def options():
        o = {"focus": st.session_state.get("opt_focus", "").strip(), "count": st.session_state.get("opt_count", 12),
             "language": st.session_state.get("opt_language", "").strip()}
        if st.session_state.get("opt_length", "default") != "default":
            o["length"] = st.session_state["opt_length"]
        return {k: v for k, v in o.items() if v}

    kinds = list(STUDIO)
    for row in range(0, len(kinds), 2):
        cols = st.columns(2)
        for col, kind in zip(cols, kinds[row:row + 2]):
            icon, title, desc = STUDIO[kind]
            if col.button(f"{icon} {title}", key=f"gen_{kind}", disabled=(not srcs) or locked, width="stretch",
                          help=lock_hint(nb) or desc):
                if start(nb, kind, options()):
                    st.rerun()

    outputs = [(k, v) for k, v in nb["outputs"].items() if isinstance(v, dict) and (v.get("kind", k) in STUDIO)]
    if not outputs:
        return
    st.divider()
    outputs.sort(key=lambda kv: kv[1].get("created") or "", reverse=True)
    for oid, out in outputs:
        kind = out.get("kind", oid)
        with st.expander(f"{STUDIO[kind][0]} {out['title']}", expanded=False):
            _render_output(nb, oid, out, locked)
            new = st.text_input("Rename", value=out["title"], key=f"rn_{nb['id']}_{oid}",
                                label_visibility="collapsed")
            if new.strip() and new.strip() != out["title"]:
                with jobs.edit(nb["id"]) as n:
                    n["outputs"][oid]["title"] = new.strip()
                st.rerun()
            if st.button("🗑 Remove", key=f"rmo_{nb['id']}_{oid}"):
                with jobs.edit(nb["id"]) as n:
                    n["outputs"].pop(oid, None)
                st.rerun()
