"""Grounded Q&A and the Studio generators (NotebookLM-style outputs).

Everything here is grounded in the notebook's *enabled* sources.
"""
from __future__ import annotations

import io
import json
import re

from studybuddy.llm import get_llm
from studybuddy.sources import build_chunks, digest, retrieve

_BROAD = re.compile(
    r"(?<![a-z])(documents?|sources?|files?|pdfs?|material|overview|summar\w*|main (topic|idea|point)s?|"
    r"what.*(is|are) (this|these|it)|tell me (more|everything)|key (points|takeaways))(?![a-z])", re.I)

_STYLE = {
    "concise": "\n- Keep the answer short: at most 3 sentences or a few bullets.",
    "detailed": "\n- Give a thorough, detailed answer with structure.",
}

NOT_FOUND = "I couldn't find that in your sources."

QA_SYSTEM = """You are a research assistant that answers ONLY from the numbered source excerpts provided.
Rules:
- Never use outside knowledge. If the excerpts do not contain the answer, reply exactly: "I couldn't find that in your sources."
- Cite every claim with the excerpt number in square brackets, like [1] or [2][3].
- Be clear and well organised; use markdown (lists, bold) when it helps.
- Answer in the user's language."""


# ------------------------------------------------------------------ helpers
def enabled_sources(nb: dict) -> list[dict]:
    return [s for s in nb["sources"] if s.get("enabled", True) and s.get("text")]


def parse_json(text: str):
    """Pull the first JSON object/array out of an LLM reply."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    pairs = [("[", "]"), ("{", "}")]
    pairs.sort(key=lambda p: text.find(p[0]) if p[0] in text else 10**9)  # outermost bracket first
    for opener, closer in pairs:
        a, b = text.find(opener), text.rfind(closer)
        if a != -1 and b > a:
            try:
                return json.loads(text[a:b + 1])
            except ValueError:
                continue
    raise ValueError("Model did not return valid JSON")


def _json_call(prompt: str, retries: int = 3):
    llm = get_llm(0.2)
    last = None
    for _ in range(retries):
        try:
            return parse_json(llm.invoke(prompt).content)
        except Exception as e:  # retry on malformed JSON
            last = e
    raise ValueError(f"Could not get structured output: {last}")


# ---------------------------------------------------------------------- Q&A
def ask(nb: dict, question: str, k: int = 6, style: str = "default"):
    """Returns (stream_generator, citations). Citations = [{n, source, text}]."""
    srcs = enabled_sources(nb)
    hits = retrieve(srcs, question, k=k)
    # Broad / "about the documents" questions share no keywords with the text, so keyword
    # retrieval finds nothing. Fall back to the opening of every source so the model can answer.
    if srcs and (not hits or _BROAD.search(question)):
        seen = {(h["source_id"], h["idx"]) for h in hits}
        overview = [c for c in build_chunks(srcs) if c["idx"] < 2 and (c["source_id"], c["idx"]) not in seen]
        hits = (hits + overview)[: max(k, 12)]
    if not hits:
        def _nf():
            yield NOT_FOUND if srcs else "Add at least one source (left panel) and I'll answer from it."
        return _nf(), []
    cites = [{"n": i, "source": h["source"], "text": h["text"]} for i, h in enumerate(hits, 1)]
    ctx = "\n\n".join(f"[{c['n']}] (from {c['source']})\n{c['text']}" for c in cites)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in nb["messages"][-7:-1]  # last turns, excluding the question just appended
    ]
    system = QA_SYSTEM + _STYLE.get(style, "")
    msgs = [{"role": "system", "content": system}, *history,
            {"role": "user", "content": f"Source excerpts:\n\n{ctx}\n\nQuestion: {question}"}]

    def gen():
        for c in get_llm(0.1).stream(msgs):
            yield c.content

    return gen(), cites


def suggest_questions(nb: dict, n: int = 4) -> list[str]:
    ctx = digest(enabled_sources(nb), 8000)
    if not ctx:
        return []
    out = _json_call(
        f"Based ONLY on these sources, write {n} interesting questions a learner could ask about them. "
        f"Return a JSON array of strings only.\n\n{ctx}"
    )
    return [str(q) for q in out][:n]


# ------------------------------------------------------------------- Studio
STUDIO = {
    "summary": ("📄", "Overview", "A clear, structured overview"),
    "study_guide": ("📘", "Study guide", "Key terms, concepts, review questions"),
    "briefing": ("📑", "Briefing doc", "Executive briefing with takeaways"),
    "faq": ("❓", "FAQ", "Questions & answers"),
    "timeline": ("🕒", "Timeline", "Chronology of events/steps"),
    "mindmap": ("🧭", "Mind map", "Concept map of the topic"),
    "flashcards": ("🃏", "Flashcards", "Q/A cards for revision"),
    "audio": ("🎧", "Audio overview", "Two-host conversation + audio"),
}

_MD_PROMPTS = {
    "summary": "Write a clear, well-structured overview of the material: a 3-4 sentence summary, then the main themes as bullet points, then 'Why it matters'.",
    "study_guide": "Create a study guide: ## Key concepts (with short explanations), ## Glossary (term - definition), ## Short-answer review questions (8) with an answer key at the end.",
    "briefing": "Write a briefing document: ## Executive summary, ## Key findings (bullets), ## Important details, ## Open questions / next steps.",
    "faq": "Write an FAQ of the 8-10 most useful questions about the material, each with a concise answer. Format: **Q:** ... then the answer.",
    "timeline": "Build a chronological timeline of events/steps/stages in the material as a markdown list: **date/stage** - what happened. If there is no real chronology, order the ideas in logical learning order and say so in one line.",
}


import contextvars  # noqa: E402

_OPTS: contextvars.ContextVar = contextvars.ContextVar("studio_options", default=None)


def _opt_text() -> str:
    o = _OPTS.get() or {}
    bits = []
    if o.get("focus"):
        bits.append("Focus especially on: " + str(o["focus"])[:300])
    if o.get("length") == "short":
        bits.append("Keep it brief.")
    elif o.get("length") == "long":
        bits.append("Be thorough and detailed.")
    if o.get("language"):
        bits.append("Write in " + str(o["language"])[:40] + ".")
    return " ".join(bits)


def _grounded(task: str, nb: dict) -> str:
    task = (task + " " + _opt_text()).strip()
    ctx = digest(enabled_sources(nb))
    if not ctx:
        raise ValueError("Add and enable at least one source first.")
    return (
        "Use ONLY the sources below. Do not invent facts. When useful, mention which source a point comes from.\n\n"
        f"{task}\n\nSOURCES:\n{ctx}"
    )


def mindmap_dot(tree: dict) -> str:
    def esc(s):
        return str(s).replace('"', "'")[:60]

    lines = ["digraph G {", 'rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#eef2ff", color="#6366f1", fontname="Helvetica"];',
             f'root [label="{esc(tree.get("central", "Topic"))}", fillcolor="#c7d2fe", fontsize=16];']
    for i, b in enumerate(tree.get("branches", [])):
        lines.append(f'b{i} [label="{esc(b.get("name", ""))}", fillcolor="#e0e7ff"]; root -> b{i};')
        for j, c in enumerate(b.get("children", [])):
            lines.append(f'b{i}_{j} [label="{esc(c)}", fillcolor="#ffffff"]; b{i} -> b{i}_{j};')
    lines.append("}")
    return "\n".join(lines)


def make_audio(segments: list[dict]) -> bytes | None:
    """Optional TTS using gTTS (two accents = two 'hosts'). Returns mp3 bytes or None."""
    try:
        from gtts import gTTS
    except Exception:
        return None
    buf = io.BytesIO()
    try:
        for seg in segments:
            tld = "com" if seg.get("speaker") == "A" else "co.uk"
            gTTS(seg["text"], lang="en", tld=tld).write_to_fp(buf)
    except Exception:
        return None
    return buf.getvalue()


def generate(kind: str, nb: dict, options: dict | None = None) -> dict:
    """Run one Studio generator. Optional options: focus, length (short|long), count, language."""
    _OPTS.set(options or {})
    icon, title, _ = STUDIO[kind]
    if kind in _MD_PROMPTS:
        md = get_llm(0.3).invoke(_grounded(_MD_PROMPTS[kind], nb)).content
        return {"title": title, "kind": kind, "markdown": md}
    if kind == "flashcards":
        cards = _json_call(_grounded(
            f"Create {int((options or {}).get('count') or 12)} flashcards. Return ONLY a JSON array of objects like "
            '{"front": "question or term", "back": "concise answer"}.', nb))
        return {"title": title, "kind": kind, "cards": [c for c in cards if "front" in c and "back" in c]}
    if kind == "mindmap":
        tree = _json_call(_grounded(
            'Build a mind map. Return ONLY JSON: {"central": "main topic", "branches": '
            '[{"name": "branch", "children": ["sub-idea", "..."]}]} with 4-7 branches, 2-5 children each, '
            "labels under 8 words.", nb))
        return {"title": title, "kind": kind, "tree": tree}
    if kind == "audio":
        script = _json_call(_grounded(
            "Write a lively 'deep dive' podcast between two hosts, A and B, explaining the material to a curious "
            'listener: 14-18 short turns. Return ONLY a JSON array of {"speaker": "A" or "B", "text": "..."}.', nb))
        segs = [{"speaker": s.get("speaker", "A"), "text": s["text"]} for s in script if s.get("text")]
        md = "\n\n".join(f"**Host {s['speaker']}:** {s['text']}" for s in segs)
        return {"title": title, "kind": kind, "markdown": md, "segments": segs}
    raise KeyError(kind)


# --------------------------------------------------------- notebook naming
DEFAULT_TITLES = ("Untitled notebook", "New notebook", "")


def suggest_title(nb: dict) -> str | None:
    """Short descriptive notebook title from the enabled sources. None if it can't be made."""
    srcs = enabled_sources(nb)
    if not srcs:
        return None
    try:
        out = get_llm(0.2).invoke(
            "Give a short, descriptive title (3 to 6 words, no quotes, no trailing punctuation) for a notebook "
            "built from these sources. Reply with the title only.\n\n" + digest(srcs, 3000)
        ).content
        title = out.strip().splitlines()[0].strip(" \"'*#.")
        return title[:60] or None
    except Exception:
        return None
