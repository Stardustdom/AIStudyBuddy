import chromadb
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

        ids = [str(abs(hash(topic + note)))]

        collection.add(
            ids=ids,
            documents=[note],
            metadatas=[{"topic": topic}]
        )

    def search(self, query, k=3):

        results = collection.query(
            query_texts=[query],
            n_results=k
        )

        return results

    def count(self):

        return collection.count()