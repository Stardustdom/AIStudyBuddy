from langchain.tools import tool
from tavily import TavilyClient
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()

# Initialize Tavily client
client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


@tool
def web_search(query: str) -> str:
    """
    Search the internet for current information.

    Use when the user asks about:
    - recent information
    - latest news
    - tutorials
    - websites
    - current events
    - online resources
    """

    print(f"\n[WEB SEARCH] {query}")

    try:
        response = client.search(
            query=query,
            max_results=1
        )

        cleaned_results = []

        for item in response.get("results", []):
            cleaned_results.append(
                {
                    "title": item.get("title", "N/A"),
                    "url": item.get("url", "N/A"),
                    "content": item.get("content", "N/A")
                }
            )

        return json.dumps(
            cleaned_results,
            indent=2
        )

    except Exception as e:
        return f"Search Error: {str(e)}"