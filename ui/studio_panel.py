import streamlit as st

from studybuddy import store
from studybuddy.studio import STUDIO, enabled_sources, generate, make_audio, mindmap_dot


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


def _render_output(nb, kind, out):
    key = f"{nb['id']}_{kind}"
    if kind == "flashcards":
        _flashcards(nb, out, key)
    elif kind == "mindmap":
        st.graphviz_chart(mindmap_dot(out["tree"]), width="stretch")
    elif kind == "audio":
        st.markdown(out["markdown"])
        audio = st.session_state.get(f"audio_{key}")
        if audio:
            st.audio(audio, format="audio/mp3")
        elif st.button("🔊 Generate audio (gTTS)", key=f"tts_{key}"):
            with st.spinner("Synthesising voices…"):
                data = make_audio(out["segments"])
            if data:
                st.session_state[f"audio_{key}"] = data
                st.rerun()
            else:
                st.warning("Audio needs the gTTS package and an internet connection. The script above is still yours.")
    else:
        st.markdown(out["markdown"])

    if out.get("markdown"):
        c1, c2 = st.columns(2)
        c1.download_button("⬇ .md", out["markdown"], f"{out['title']}.md", key=f"dl_{key}", width="stretch")
        if c2.button("📌 To notes", key=f"pin_{key}", width="stretch"):
            nb["notes"].append({"title": out["title"], "content": out["markdown"]})
            store.save(nb)
            st.toast("Saved to Notes 📌")


def render_studio(nb):
    st.subheader("Studio")
    srcs = enabled_sources(nb)
    if not srcs:
        st.caption("Enable at least one source to unlock the Studio.")

    kinds = list(STUDIO)
    for row in range(0, len(kinds), 2):
        cols = st.columns(2)
        for col, kind in zip(cols, kinds[row:row + 2]):
            icon, title, desc = STUDIO[kind]
            done = kind in nb["outputs"]
            if col.button(f"{icon} {title}", key=f"gen_{kind}", disabled=not srcs, width="stretch",
                          help=desc + (" (click to regenerate)" if done else ""),
                          type="secondary"):
                with st.spinner(f"Generating {title.lower()}…"):
                    try:
                        nb["outputs"][kind] = generate(kind, nb)
                        st.session_state[f"open_{nb['id']}"] = kind
                        st.session_state.pop(f"audio_{nb['id']}_{kind}", None)
                        store.save(nb)
                    except Exception as e:
                        st.error(f"{title}: {e}")
                st.rerun()

    if not nb["outputs"]:
        return
    st.divider()
    opened = st.session_state.get(f"open_{nb['id']}")
    for kind, out in nb["outputs"].items():
        if kind not in STUDIO:
            continue
        with st.expander(f"{STUDIO[kind][0]} {out['title']}", expanded=(kind == opened)):
            _render_output(nb, kind, out)
            if st.button("🗑 Remove", key=f"rmo_{nb['id']}_{kind}"):
                del nb["outputs"][kind]
                store.save(nb)
                st.rerun()
