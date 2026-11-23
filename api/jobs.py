"""Per-notebook job lock + background job runner.

Exactly one job (chat answer OR studio generation) may be active per notebook;
the lock is enforced here, on the server, regardless of what the client does.
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field

from studybuddy import store
from studybuddy.llm import CANCEL_EVENT, Cancelled

JOB_TIMEOUT_S = 15 * 60


class Busy(Exception):
    def __init__(self, job: "Job"):
        self.job = job


class NotFound(Exception):
    pass


@dataclass
class Job:
    id: str
    nb_id: str
    kind: str
    label: str
    status: str = "running"  # running | done | failed | cancelled
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    output_id: str | None = None
    error: str | None = None
    cancel: threading.Event = field(default_factory=threading.Event)

    def public(self) -> dict:
        return {
            "job_id": self.id, "kind": self.kind, "label": self.label, "status": self.status,
            "started_at": self.started_at, "finished_at": self.finished_at,
            "output_id": self.output_id, "error": self.error,
        }


# ---------------------------------------------------------- notebook edit lock
_nb_locks: dict[str, threading.RLock] = {}
_nb_locks_guard = threading.Lock()


def _lock_for(nb_id: str) -> threading.RLock:
    with _nb_locks_guard:
        return _nb_locks.setdefault(nb_id, threading.RLock())


def ensure_ids(nb: dict) -> None:
    """Older (Streamlit-era) messages/notes have no ids; give them stable ones."""
    for coll, prefix in (("messages", "m"), ("notes", "n")):
        for item in nb.get(coll, []):
            item.setdefault("id", prefix + uuid.uuid4().hex[:8])
    for t in nb.get("study", []):
        t.setdefault("id", "t" + uuid.uuid4().hex[:8])


@contextmanager
def edit(nb_id: str):
    """Serialised load -> mutate -> save of one notebook."""
    with _lock_for(nb_id):
        nb = store.load(nb_id)
        if nb is None:
            raise NotFound(nb_id)
        ensure_ids(nb)
        yield nb
        store.save(nb)


def read(nb_id: str) -> dict:
    nb = store.load(nb_id)
    if nb is None:
        raise NotFound(nb_id)
    ensure_ids(nb)
    return nb


# ------------------------------------------------------------------ job state
_state = threading.Lock()
_jobs: dict[str, Job] = {}      # job_id -> Job
_active: dict[str, str] = {}    # nb_id -> job_id


def _expire_locked(nb_id: str) -> None:
    jid = _active.get(nb_id)
    job = _jobs.get(jid) if jid else None
    if job and job.status == "running" and time.time() - job.started_at > JOB_TIMEOUT_S:
        job.cancel.set()
        job.status, job.error, job.finished_at = "failed", "Timed out", time.time()
        _active.pop(nb_id, None)


def active(nb_id: str) -> Job | None:
    with _state:
        _expire_locked(nb_id)
        jid = _active.get(nb_id)
        return _jobs.get(jid) if jid else None


def begin(nb_id: str, kind: str, label: str) -> Job:
    """Take the notebook's single job slot or raise Busy. Atomic - double clicks can't start two jobs."""
    with _state:
        _expire_locked(nb_id)
        jid = _active.get(nb_id)
        if jid and _jobs[jid].status == "running":
            raise Busy(_jobs[jid])
        job = Job(id=uuid.uuid4().hex[:10], nb_id=nb_id, kind=kind, label=label)
        _jobs[job.id] = job
        _active[nb_id] = job.id
        for old in [j for j in _jobs.values() if j.finished_at and time.time() - j.finished_at > 3600]:
            _jobs.pop(old.id, None)  # forget old finished jobs
        return job


def finish(job: Job, status: str, error: str | None = None, output_id: str | None = None) -> None:
    with _state:
        if job.status == "running":  # a cancel/timeout may already have settled it
            job.status, job.error, job.output_id = status, error, output_id
            job.finished_at = time.time()
        if _active.get(job.nb_id) == job.id:
            _active.pop(job.nb_id, None)


def cancel(nb_id: str, job_id: str) -> Job:
    with _state:
        job = _jobs.get(job_id)
        if job is None or job.nb_id != nb_id:
            raise NotFound(job_id)
        if job.status == "running":
            job.cancel.set()
            job.status, job.finished_at = "cancelled", time.time()
        if _active.get(nb_id) == job_id:
            _active.pop(nb_id, None)  # lock is released immediately
        return job


def get(nb_id: str, job_id: str) -> Job:
    with _state:
        job = _jobs.get(job_id)
        if job is None or job.nb_id != nb_id:
            raise NotFound(job_id)
        _expire_locked(nb_id)
        return job


def run_in_thread(job: Job, work) -> None:
    """work(job) -> commit(nb) -> output_id. Compute happens unlocked; commit is applied under the notebook lock,
    and only if the job was not cancelled meanwhile."""

    def target():
        CANCEL_EVENT.set(job.cancel)
        try:
            commit = work(job)
            if job.cancel.is_set() or job.status != "running":
                return
            out_id = None
            with edit(job.nb_id) as nb:
                if job.status == "running":
                    out_id = commit(nb)
            finish(job, "done", output_id=out_id)
        except Cancelled:
            finish(job, "cancelled")
        except NotFound:
            finish(job, "failed", "Notebook no longer exists")
        except BaseException as e:  # noqa: BLE001 - report every failure, never leave the lock held
            finish(job, "failed", str(e) or type(e).__name__)

    threading.Thread(target=target, daemon=True, name=f"job-{job.id}").start()
