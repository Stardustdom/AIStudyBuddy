"""Notebook persistence: one JSON file per notebook in data/notebooks/.

A notebook = sources + grounded chat + saved notes + studio outputs + study tracks
(the planner -> researcher -> quiz -> evaluator pipeline results).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(BASE, "data", "notebooks")
OLD_HISTORY = os.path.join(BASE, "memory", "chat_history.json")


def _path(nb_id: str) -> str:
    return os.path.join(DIR, f"{nb_id}.json")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_notebook(title: str = "Untitled notebook") -> dict:
    return {
        "id": uuid.uuid4().hex[:10],
        "title": title,
        "created": _now(),
        "modified": _now(),
        "sources": [],
        "messages": [],
        "notes": [],
        "outputs": {},
        "study": [],
    }


def save(nb: dict) -> None:
    os.makedirs(DIR, exist_ok=True)
    nb["modified"] = _now()
    tmp = _path(nb["id"]) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _path(nb["id"]))


def load(nb_id: str) -> dict | None:
    try:
        with open(_path(nb_id), encoding="utf-8") as f:
            nb = json.load(f)
    except (OSError, ValueError):
        return None
    for k, v in new_notebook().items():  # forward-compatible defaults
        nb.setdefault(k, v)
    return nb


def delete(nb_id: str) -> None:
    try:
        os.remove(_path(nb_id))
    except OSError:
        pass


def list_notebooks() -> list[dict]:
    """[{id,title,modified,n_sources}] newest first."""
    _migrate_old_chats()
    out = []
    if os.path.isdir(DIR):
        for fn in os.listdir(DIR):
            if fn.endswith(".json"):
                nb = load(fn[:-5])
                if nb:
                    out.append(
                        {"id": nb["id"], "title": nb["title"], "modified": nb["modified"], "n_sources": len(nb["sources"])}
                    )
    return sorted(out, key=lambda x: x["modified"], reverse=True)


def import_json(raw: bytes) -> dict:
    nb = json.loads(raw.decode("utf-8"))
    for k, v in new_notebook().items():
        nb.setdefault(k, v)
    nb["id"] = uuid.uuid4().hex[:10]  # never clobber an existing notebook
    save(nb)
    return nb


def export_markdown(nb: dict) -> str:
    lines = [f"# {nb['title']}", ""]
    if nb["sources"]:
        lines += ["## Sources", *[f"- {s['name']} ({s['kind']})" for s in nb["sources"]], ""]
    if nb["notes"]:
        lines += ["## Saved notes", ""]
        for n in nb["notes"]:
            lines += [f"### {n['title']}", n["content"], ""]
    for key, out in nb["outputs"].items():
        if isinstance(out, dict) and out.get("markdown"):
            lines += [f"## {out.get('title', key)}", out["markdown"], ""]
    lines += ["## Chat", ""]
    for m in nb["messages"]:
        who = "**You**" if m["role"] == "user" else "**Study Buddy**"
        lines += [f"{who}: {m['content']}", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- migration
_MIGRATED = os.path.join(DIR, ".migrated")


def _migrate_old_chats() -> None:
    """One-time import of the old chat-style history (memory/chat_history.json)."""
    if os.path.exists(_MIGRATED) or not os.path.exists(OLD_HISTORY):
        return
    os.makedirs(DIR, exist_ok=True)
    try:
        with open(OLD_HISTORY, encoding="utf-8") as f:
            old = json.load(f)
        for cid, chat in old.items():
            msgs = chat.get("messages") or []
            state = chat.get("state") or {}
            study = state.get("workspace") or []
            if not msgs and not study:
                continue
            nb = new_notebook(chat.get("title") or "Imported chat")
            nb["id"] = cid.replace("-", "")[:10]
            nb["created"] = chat.get("created_at", nb["created"])
            nb["messages"] = [{"role": m["role"], "content": m["content"]} for m in (state.get("messages") or msgs)]
            nb["study"] = study
            save(nb)
    except Exception:
        pass
    with open(_MIGRATED, "w") as f:
        f.write("1")
