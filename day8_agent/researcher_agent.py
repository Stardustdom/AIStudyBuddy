from langchain.tools import tool
from tavily import TavilyClient
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from memory.long_term import LongTermMemory
import os

# Load environment variables
load_dotenv()

# Tavily client
client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)

# Ollama LLM
llm = ChatOllama(
    model="mistral",
    temperature=0.1
)

# Long-term memory
ltm = LongTermMemory()


@tool
def researcher(subtopic: str) -> dict:
    """
    Search the web and generate structured study notes.
    """

    print(f"\n[SEARCHING] {subtopic}")

    try:
        # Search Tavily
        search_results = client.search(
            query=subtopic,
            max_results=5
        )

        # Extract useful content
        content = "\n\n".join(
            result["content"]
            for result in search_results["results"]
        )

        # Prompt for Mistral
        prompt = f"""
You are an expert teacher creating study notes for beginners.

Topic:
{subtopic}

Web Content:
{content}

Instructions:

1. Assume the student has no prior knowledge.
2. Explain the topic in simple language.
3. Focus on understanding rather than documentation.
4. Organize the notes into:
   - Introduction
   - Key Concepts
   - Important Features
   - Example
   - Summary
5. Include practical examples whenever possible.
6. Ignore installation manuals, configuration details, package managers, version numbers, and server-specific instructions unless they are central to understanding the topic.
7. Do NOT mention websites, tutorials, sources, or URLs.
8. Output only study notes.
"""

        response = llm.invoke(prompt)

        # Save to ChromaDB
        ltm.add_note(subtopic, response.content)

        return {
            "topic": subtopic,
            "notes": response.content
        }

    except Exception as e:
        return {
            "topic": subtopic,
            "notes": f"Error: {str(e)}"
        }