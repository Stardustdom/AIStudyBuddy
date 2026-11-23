import streamlit as st

from studybuddy import store
from studybuddy.sources import extract_file, fetch_url, make_source, web_search

ICON = {"pdf": "📕", "docx": "📘", "url": "🌐", "text": "📝", "web": "🔎"}


def _add(nb, src):
    nb["sources"].append(src)
    store.save(nb)


def render_sources(nb):
    st.subheader("Sources")

    # ----------------------------------------------------------- upload
    n = st.session_state.get("uploader_n", 0)
    files = st.file_uploader(
        "Upload documents",
        type=["pdf", "docx", "txt", "md", "csv"],
        accept_multiple_files=True,
        key=f"uploader_{n}",
        help="PDF, Word, text, markdown or CSV. Added automatically.",
    )
    if files:
        added = 0
        for f in files:
            try:
                text = extract_file(f.name, f.getvalue())
            except Exception as e:
                st.error(f"{f.name}: {e}")
                continue
            if not text:
                st.warning(f"{f.name}: no readable text (scanned PDF?).")
                continue
            ext = f.name.rsplit(".", 1)[-1].lower()
            _add(nb, make_source(f.name, ext if ext in ("pdf", "docx") else "text", text))
            added += 1
        st.session_state.uploader_n = n + 1  # reset the uploader so files aren't re-added
        if added:
            st.toast(f"Added {added} source(s)")
        st.rerun()

    # ------------------------------------------------- other ways to add
    t_url, t_text, t_web = st.tabs(["🌐 Website", "📝 Paste", "🔎 Discover"])

    with t_url:
        url = st.text_input("Page or PDF URL", key="src_url", placeholder="https://…")
        if st.button("Add website", width="stretch", disabled=not url):
            with st.spinner("Fetching…"):
                try:
                    title, text = fetch_url(url.strip())
                    if len(text) < 200:
                        st.warning("That page has almost no readable text.")
                    else:
                        _add(nb, make_source(title[:80], "url", text, url=url.strip()))
                        st.rerun()
                except Exception as e:
                    st.error(f"Couldn't fetch: {e}")

    with t_text:
        title = st.text_input("Title", key="src_ptitle", placeholder="My notes")
        body = st.text_area("Text", key="src_pbody", height=120, placeholder="Paste anything…")
        if st.button("Add text", width="stretch", disabled=not body.strip()):
            _add(nb, make_source(title.strip() or "Pasted text", "text", body))
            st.session_state.src_pbody = ""
            st.session_state.src_ptitle = ""
            st.rerun()

    with t_web:
        q = st.text_input("Find sources on the web", key="src_q", placeholder="e.g. photosynthesis light reactions")
        if st.button("Search", width="stretch", disabled=not q):
            try:
                with st.spinner("Searching…"):
                    st.session_state.web_results = web_search(q)
            except Exception as e:
                st.error(str(e))
        for i, r in enumerate(st.session_state.get("web_results", [])):
            with st.container(border=True):
                st.markdown(f"**{r.get('title', 'Result')[:70]}**")
                st.caption((r.get("content") or "")[:160] + "…")
                if st.button("➕ Add as source", key=f"web_add_{i}", width="stretch"):
                    with st.spinner("Importing…"):
                        try:
                            _, text = fetch_url(r["url"])
                            if len(text) < 200:
                                text = r.get("content", "")
                        except Exception:
                            text = r.get("content", "")
                    _add(nb, make_source(r.get("title", "Web result")[:80], "web", text, url=r.get("url")))
                    st.session_state.web_results.pop(i)
                    st.rerun()

    st.divider()

    # ------------------------------------------------------------- list
    srcs = nb["sources"]
    if not srcs:
        st.info("No sources yet. Upload a PDF, add a website, or paste text — everything the assistant says will be grounded in them.")
        return

    all_on = all(s.get("enabled", True) for s in srcs)
    if st.checkbox(f"Select all ({len(srcs)})", value=all_on, key=f"all_{nb['id']}_{len(srcs)}_{all_on}") != all_on:
        for s in srcs:
            s["enabled"] = not all_on
        store.save(nb)
        st.rerun()

    for s in list(srcs):
        c1, c2 = st.columns([6, 1], vertical_alignment="center")
        on = c1.checkbox(
            f"{ICON.get(s['kind'], '📄')} {s['name'][:34]}",
            value=s.get("enabled", True),
            key=f"on_{s['id']}",
            help=f"{s['chars']:,} characters",
        )
        if on != s.get("enabled", True):
            s["enabled"] = on
            store.save(nb)
            st.rerun()
        if c2.button("✕", key=f"rm_{s['id']}", help="Remove source"):
            nb["sources"] = [x for x in srcs if x["id"] != s["id"]]
            store.save(nb)
            st.rerun()
        with c1.expander("preview", expanded=False):
            st.caption(s["text"][:1200] + ("…" if s["chars"] > 1200 else ""))

    active = sum(1 for s in srcs if s.get("enabled", True))
    st.caption(f"{active} of {len(srcs)} source(s) active — only checked sources are used.")
