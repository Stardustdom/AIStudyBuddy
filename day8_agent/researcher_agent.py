"""Researcher agent.

Two modes:
* grounded  - writes study notes strictly from the user's uploaded sources
              (retrieved with BM25), the NotebookLM way.
* web       - searches the web (Tavily) and writes notes; falls back to the
              model's own knowledge if no search key is configured.
"""
from langchain_core.tools import tool

from memory.long_term import LongTermMemory
from studybuddy.llm import get_llm, setting
from studybuddy.sources import retrieve, web_search

ltm = LongTermMemory()

NOTES_FORMAT = """Write beginner-friendly study notes with these sections:

1. Introduction
2. Key Concepts
3. Important Features
4. Example
5. Summary

Do NOT mention websites, URLs or tutorials. Return only the study notes in markdown."""


def research_from_sources(subtopic: str, sources: list) -> dict:
    """Grounded research: notes built only from the user's own documents."""
    hits = retrieve(sources, subtopic, k=8)
    if not hits:
        return {
            "topic": subtopic,
            "notes": f"_No passage about **{subtopic}** was found in your sources._",
            "grounded": True,
        }
    ctx = "\n\n".join(f"(from {h['source']})\n{h['text']}" for h in hits)
    prompt = (
        f"You are an expert teacher. Using ONLY the source excerpts below, create study notes on:\n"
        f"{subtopic}\n\nIf the excerpts do not cover something, leave it out - never invent facts.\n\n"
        f"{NOTES_FORMAT}\n\nSOURCE EXCERPTS:\n{ctx}"
    )
    notes = get_llm(0.1).invoke(prompt).content
    return {"topic": subtopic, "notes": notes, "grounded": True,
            "from_sources": sorted({h["source"] for h in hits})}


@tool
def researcher(subtopic: str) -> dict:
    """Search the web and generate structured study notes."""
    try:
        web = ""
        if setting("TAVILY_API_KEY"):
            results = web_search(subtopic, max_results=5)
            web = "\n\n".join(r.get("content", "") for r in results)
        prompt = f"You are an expert teacher creating study notes.\n\nTopic:\n{subtopic}\n\n"
        if web:
            prompt += f"Web Content:\n{web}\n\n"
        prompt += NOTES_FORMAT
        notes = get_llm(0.1).invoke(prompt).content
        ltm.add_note(topic=subtopic, note=notes)
        return {"topic": subtopic, "notes": notes}
    except Exception as e:
        return {"topic": subtopic, "notes": f"Error: {e}"}
