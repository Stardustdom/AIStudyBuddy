"""Context agent: answers questions grounded in the notebook's sources.

The retrieval + citation logic lives in studybuddy.studio.ask (BM25 over the
enabled sources). This module keeps the agent's public entry point.
"""
from studybuddy.studio import ask


def stream_answer_from_context(notebook: dict, question: str):
    """Returns (token_stream, citations) for a question about the notebook's sources."""
    return ask(notebook, question)


def answer_from_context(notebook: dict, question: str):
    stream, cites = ask(notebook, question)
    return "".join(stream), cites
