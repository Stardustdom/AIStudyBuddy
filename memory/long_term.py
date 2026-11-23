"""Long-term memory: cache of researched study notes.

Same interface as the old ChromaDB version (add_note / get_note / search) but
stored as JSON and searched with BM25, so there is no embedding model or vector
DB to install - which keeps the app deployable on Streamlit Community Cloud.
"""
import json
import os

from studybuddy.sources import retrieve

_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "long_term_notes.json"
)


class LongTermMemory:
    def _load(self) -> dict:
        try:
            with open(_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def add_note(self, topic, note):
        data = self._load()
        data[topic] = note
        os.makedirs(os.path.dirname(_FILE), exist_ok=True)
        with open(_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)

    def get_note(self, topic):
        """Exact lookup. Shape matches chroma's get(): {'documents': [...]}"""
        note = self._load().get(topic)
        return {"documents": [note] if note else []}

    def search(self, query, k=3):
        """BM25 search over cached notes. Shape matches chroma's query(): {'documents': [[...]]}"""
        pseudo = [{"id": t, "name": t, "text": n} for t, n in self._load().items()]
        hits = retrieve(pseudo, query, k=k)
        return {"documents": [[h["text"] for h in hits]]}

    def count(self):
        return len(self._load())
