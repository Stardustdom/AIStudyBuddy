"""Source ingestion (PDF / DOCX / TXT / MD / CSV / URL / pasted text / web search)
and lightweight BM25 retrieval over the enabled sources of a notebook.

Retrieval is pure Python on purpose: no embedding model or vector DB to install,
so the app deploys on Streamlit Community Cloud without heavy dependencies.
"""
from __future__ import annotations

import io
import math
import re
import uuid
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser

MAX_SOURCE_CHARS = 400_000

# ----------------------------------------------------------------- extraction


def _clean(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_file(name: str, data: bytes) -> str:
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
    if ext == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        pages = []
        for i, p in enumerate(reader.pages, 1):
            t = p.extract_text() or ""
            if t.strip():
                pages.append(f"[Page {i}]\n{t}")
        return _clean("\n\n".join(pages))
    if ext == "docx":
        from docx import Document

        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text.strip() for c in row.cells))
        return _clean("\n".join(parts))
    # txt, md, csv, json, code...
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return _clean(data.decode(enc))
        except Exception:
            continue
    return ""


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "footer", "header", "svg", "form"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag == "title":
            self._in_title = True
        if tag in {"p", "br", "div", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip:
            self.parts.append(data)


def fetch_url(url: str) -> tuple[str, str]:
    """Return (title, text) for a web page."""
    import requests

    if not re.match(r"^https?://", url):
        url = "https://" + url
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (StudyBuddy)"})
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        return url.rsplit("/", 1)[-1], extract_file("x.pdf", r.content)
    p = _TextExtractor()
    p.feed(r.text)
    return p.title.strip() or url, _clean("".join(p.parts))


_YT = re.compile(r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})")


def youtube_id(url: str):
    m = _YT.search(url)
    return m.group(1) if m else None


def fetch_youtube(url: str) -> tuple[str, str]:
    """Return (title, transcript) for a YouTube video. Raises if it has no transcript."""
    import requests

    vid = youtube_id(url)
    if not vid:
        raise ValueError("Not a valid YouTube link")
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as e:
        raise RuntimeError("youtube-transcript-api is not installed") from e
    try:
        if hasattr(YouTubeTranscriptApi, "get_transcript"):  # <1.0
            parts = YouTubeTranscriptApi.get_transcript(vid)
            text = " ".join(p["text"] for p in parts)
        else:
            fetched = YouTubeTranscriptApi().fetch(vid)
            text = " ".join(sn.text for sn in fetched)
    except Exception as e:
        raise ValueError(f"No transcript available for this video ({type(e).__name__}).") from e
    title = vid
    try:
        r = requests.get("https://www.youtube.com/oembed", params={"url": url, "format": "json"}, timeout=10)
        if r.ok:
            title = r.json().get("title", vid)
    except Exception:
        pass
    return title, _clean(text)


def web_search(query: str, max_results: int = 6) -> list[dict]:
    """Search the web through Tavily. Returns [{title,url,content}]. Needs TAVILY_API_KEY."""
    import requests

    from studybuddy.llm import setting

    key = setting("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY is not set, so web discovery is unavailable.")
    r = requests.post(
        "https://api.tavily.com/search",
        json={"api_key": key, "query": query, "max_results": max_results},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("results", [])


# --------------------------------------------------------------------- model


def make_source(name: str, kind: str, text: str, url: str | None = None) -> dict:
    text = _clean(text)[:MAX_SOURCE_CHARS]
    return {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "kind": kind,
        "url": url,
        "text": text,
        "chars": len(text),
        "enabled": True,
        "added": datetime.now().isoformat(timespec="seconds"),
    }


# ----------------------------------------------------------------- retrieval

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = set(
    "a an the and or of to in on for with is are was were be been it this that these those as at by from "
    "what which who whom how why when where do does did can could should would about into than then so if "
    "not no yes i you he she we they me my your our their its".split()
)


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1]


def chunk_text(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces = []
    for p in paras:  # hard-split paragraphs longer than one chunk, with overlap
        if len(p) <= size:
            pieces.append(p)
        else:
            pieces += [p[i:i + size] for i in range(0, len(p), size - overlap)]
    chunks, cur = [], ""
    for p in pieces:
        if len(cur) + len(p) + 2 <= size:
            cur = f"{cur}\n\n{p}".strip()
        else:
            if cur:
                chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)
    return chunks


def build_chunks(sources: list[dict]) -> list[dict]:
    out = []
    for s in sources:
        for i, c in enumerate(chunk_text(s["text"])):
            out.append({"source_id": s["id"], "source": s["name"], "idx": i, "text": c})
    return out


def retrieve(sources: list[dict], query: str, k: int = 6) -> list[dict]:
    """BM25 top-k chunks across the given sources."""
    chunks = build_chunks(sources)
    q = tokens(query)
    if not chunks or not q:
        return []
    docs = [Counter(tokens(c["text"])) for c in chunks]
    lens = [sum(d.values()) or 1 for d in docs]
    avg = sum(lens) / len(lens)
    n = len(chunks)
    df = Counter()
    for d in docs:
        for t in set(d):
            df[t] += 1
    k1, b = 1.5, 0.75
    scored = []
    for c, d, ln in zip(chunks, docs, lens):
        s = 0.0
        for t in set(q):
            f = d.get(t, 0)
            if not f:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * ln / avg))
        if s > 0:
            scored.append((s, c))
    scored.sort(key=lambda x: -x[0])
    return [dict(c, score=round(s, 3)) for s, c in scored[:k]]


def digest(sources: list[dict], budget: int = 24_000) -> str:
    """Whole-source context for summaries/guides: an even share of the budget per source."""
    if not sources:
        return ""
    per = max(budget // len(sources), 1500)
    parts = []
    for s in sources:
        t = s["text"]
        if len(t) > per:  # keep the start and a slice of the end
            head = int(per * 0.7)
            t = t[:head] + "\n[...]\n" + t[-(per - head):]
        parts.append(f"=== SOURCE: {s['name']} ===\n{t}")
    return "\n\n".join(parts)
