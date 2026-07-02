from langchain.tools import tool
from tavily import TavilyClient
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from memory.long_term import LongTermMemory
import os

load_dotenv()

client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)

llm = ChatOllama(
    model="mistral",
    temperature=0.1
)

ltm = LongTermMemory()


@tool
def researcher(subtopic: str) -> dict:
    """
    Search the web and generate structured study notes.
    """

    print(f"\n[SEARCHING WEB] {subtopic}")

    try:

        search_results = client.search(
            query=subtopic,
            max_results=5
        )

        content = "\n\n".join(
            result["content"]
            for result in search_results["results"]
        )

        prompt = f"""
You are an expert teacher creating study notes.

Topic:
{subtopic}

Web Content:
{content}

Write beginner-friendly notes with the following sections:

1. Introduction
2. Key Concepts
3. Important Features
4. Example
5. Summary

Do NOT mention websites, URLs or tutorials.
Return only study notes.
"""

        response = llm.invoke(prompt)

        ltm.add_note(
            topic=subtopic,
            note=response.content
        )

        return {
            "topic": subtopic,
            "notes": response.content
        }

    except Exception as e:

        return {
            "topic": subtopic,
            "notes": f"Error: {e}"
        }