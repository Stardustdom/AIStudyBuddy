import chromadb
import hashlib
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_or_create_collection(
    name="study_notes",
    embedding_function=embedding_function
)


class LongTermMemory:

    def add_note(self, topic, note):
        """
        Save a note into ChromaDB.
        Each topic has a unique ID so duplicate topics aren't stored.
        """

        doc_id = hashlib.sha256(topic.encode()).hexdigest()

        # Remove existing note if present
        try:
            collection.delete(ids=[doc_id])
        except Exception:
            pass

        collection.add(
            ids=[doc_id],
            documents=[note],
            metadatas=[{"topic": topic}]
        )

    def get_note(self, topic):
        """
        Retrieve notes only if the exact topic exists.
        """

        return collection.get(
            where={"topic": topic}
        )

    def count(self):
        return collection.count()