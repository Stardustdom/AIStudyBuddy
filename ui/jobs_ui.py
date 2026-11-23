"""Streamlit glue for the global job lock.

Studio / study-path / quiz tasks run as background jobs (api.jobs) so the script returns immediately,
the UI can stay responsive, and every trigger can be disabled while one job is active.
"""
import streamlit as st

from api import jobs
from studybuddy import tasks


def settings_for_thread() -> dict:
    """Keys typed in the sidebar live in st.session_state, which worker threads can't read."""
    return {k[4:]: v for k, v in st.session_state.items()
            if isinstance(k, str) and k.startswith("cfg_") and v and v != "auto"}


def is_locked(nb: dict) -> bool:
    return jobs.active(nb["id"]) is not None


def lock_hint(nb: dict) -> str | None:
    j = jobs.active(nb["id"])
    return f"{j.label} is still running. Stop it or wait." if j else None


def start(nb: dict, kind: str, options: dict | None = None) -> bool:
    """Start a background job. Returns True if it started. Never starts two (server-side lock)."""
    try:
        work = tasks.make_work(nb, kind, options or {})
    except tasks.TaskError as e:
        st.toast(e.message, icon="⚠️")
        return False
    try:
        job = jobs.begin(nb["id"], kind, tasks.label(kind))
    except jobs.Busy as b:
        st.toast(f"{b.job.label} is still running. Stop it or wait.", icon="⏳")
        return False
    st.session_state[f"jid_{nb['id']}"] = job.id
    jobs.run_in_thread(job, work, settings_for_thread())
    return True


@st.dialog("Generation in progress")
def leave_dialog(nb: dict, on_leave):
    j = jobs.active(nb["id"])
    st.write(f"**{j.label if j else 'A job'}** is still running. Leave and stop it?")
    c1, c2 = st.columns(2)
    if c1.button("Stop and leave", type="primary", width="stretch"):
        if j:
            jobs.cancel(nb["id"], j.id)
        on_leave()
    if c2.button("Stay", width="stretch"):
        st.rerun()


def render_jobbar(nb: dict) -> None:
    """Status pill + Stop while a job runs; reports the outcome of a job that just finished."""
    done = st.session_state.pop("job_done", None)
    if done:
        status, error, label = done
        if status == "failed":
            st.error(f"{label} failed: {error}")
        elif status == "done":
            st.toast(f"{label} — done", icon="✅")
        elif status == "cancelled":
            st.toast(f"{label} stopped", icon="⏹")

    if jobs.active(nb["id"]) is None:
        return

    @st.fragment(run_every=1.5)
    def _bar():
        j = jobs.active(nb["id"])
        if j is None:  # finished (or stopped elsewhere): report once and refresh the whole page
            jid = st.session_state.get(f"jid_{nb['id']}")
            if jid:
                try:
                    f = jobs.get(nb["id"], jid)
                    st.session_state.job_done = (f.status, f.error, f.label)
                except jobs.NotFound:
                    pass
            st.rerun()
        elapsed = int(__import__("time").time() - j.started_at)
        c1, c2 = st.columns([6, 1], vertical_alignment="center")
        c1.markdown(
            f'<div class="sb-job"><span class="sb-spin"></span><b>{j.label}…</b>'
            f'<span class="sb-job-t">{elapsed}s</span></div>',
            unsafe_allow_html=True,
        )
        if c2.button("■ Stop", key="stop_job", width="stretch", help="Cancel this generation"):
            jobs.cancel(nb["id"], j.id)
            st.session_state.job_done = ("cancelled", None, j.label)
            st.rerun()

    _bar()
