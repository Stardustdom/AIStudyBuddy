import hashlib
import chromadb
from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction
)

embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.get_or_create_collection(
    name="study_notes",
    embedding_function=embedding_function
)


class LongTermMemory:

    # ==========================================
    # Save
    # ==========================================

    def add_note(self, topic, note):

        doc_id = hashlib.sha256(
            topic.encode()
        ).hexdigest()

        try:
            collection.delete(ids=[doc_id])
        except:
            pass

        collection.add(

            ids=[doc_id],

            documents=[note],

            metadatas=[
                {
                    "topic": topic
                }
            ]

        )

    # ==========================================
    # Exact lookup
    # ==========================================

    def get_note(self, topic):

        return collection.get(

            where={
                "topic": topic
            }

        )

    # ==========================================
    # Semantic Search ⭐
    # ==========================================

    def search(self, query, k=3):

        results = collection.query(

            query_texts=[query],

            n_results=k

        )

        return results

    # ==========================================
    # Count
    # ==========================================

    def count(self):

        return collection.count()