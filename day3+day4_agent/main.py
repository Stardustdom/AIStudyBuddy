import re
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama

# Import both tools
from searchtool import web_search
from toolsCalc import calculator

# 1. Unified System Prompt handling both search and calculator restrictions
SYSTEM_PROMPT = """You are a helpful, direct AI Study Buddy with access to tools.

CRITICAL TOOL RULES:
1. CALCULATOR TOOL: Use ONLY when there is an explicit mathematical expression or calculation request containing numbers and arithmetic operators (+, -, *, /, percentages, equations). NEVER calculate manually.
2. WEB SEARCH TOOL: Use ONLY for factual queries, tutorials, news, websites, or current events that require external data.
3. CHAT MODE: If no tool is needed, respond naturally like a human friend.

CRITICAL EXECUTION RULES:
- NEVER mention "modes", "CHAT MODE", "SEARCH MODE", or tool names in your final response.
- NEVER explain your reasoning or why you chose to use or not use a tool.
- Do not output mock JSON, internal thoughts, or prefixes like "No calculation is required" or "Based on the web search".
- If a message contains BOTH conversation and a tool requirement (e.g., "Hello, what is 5*8?"), greet the user naturally and include the tool's result seamlessly.
- Always use the EXACT values returned by the tools. Never modify or round them unless asked.
"""

# 2. Initialize the LLM (temperature=0 is best for reliable tool usage)
model = ChatOllama(
    model="llama3.1:8b",
    temperature=0
)

# 3. Build the single agent with both tools
agent = create_agent(
    model=model,
    tools=[web_search, calculator],
    system_prompt=SYSTEM_PROMPT
)

messages = []

# 4. Code-level bypass for greetings and short conversational triggers
CONVERSATIONAL_BYPASS = {
    "hello", "hi", "hey", "how are you", "how're you", 
    "good morning", "good afternoon", "good evening",
    "whats up", "what's up", "yo", "thank you", "thanks", 
    "no", "yes", "ok", "okay", "bye", "sure", "cool", "got it"
}

print("=== AI Study Buddy (Search + Calculator) ===")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        print("Goodbye!")
        break

    # Strip punctuation and normalize spacing
    cleaned_input = re.sub(r'[^\w\s]', '', user_input.strip().lower())
    
    # Catch conversational filler and ultra-short inputs locally to save compute
    if cleaned_input in CONVERSATIONAL_BYPASS or (len(cleaned_input.split()) <= 1 and len(cleaned_input) < 4):
        if "thank" in cleaned_input:
            reply = "You're very welcome! Let me know if anything else comes up."
        elif cleaned_input in {"no", "bye", "goodbye"}:
            reply = "Alright! Feel free to reach out if you need help later. Have a great day!"
        elif "how are you" in cleaned_input or "whats up" in cleaned_input:
            reply = "I'm doing great, thank you for asking! How can I assist you today?"
        elif cleaned_input in {"sure", "ok", "okay", "cool", "got it"}:
            reply = "Sounds good! Let me know whenever you're ready for the next question."
        else:
            reply = "Hello! How can I assist you today?"
            
        print(f"\nAgent: {reply}\n")
        
        messages.append(HumanMessage(content=user_input))
        messages.append(AIMessage(content=reply))
        continue

    # 5. Let the LangChain agent handle factual/search or mathematical inputs
    print("\nProcessing...\n")
    messages.append(HumanMessage(content=user_input))

    try:
        response = agent.invoke({"messages": messages})
        final_message = response["messages"][-1]
        
        # --- Python Sanitization Fallback ---
        clean_output = final_message.content
        
        phrases_to_strip = [
            "No calculation is required to answer your question. I'll just respond normally.",
            "However, I can still respond naturally like a human friend",
            "No calculation is required for your greeting.",
            "No calculation is required for your response.",
            "No calculation is required for your question.",
            "No calculation is required to answer your question.",
            "There is no calculation needed for your question.",
            "The result of the calculation is",
            "As for the calculation,",
            "Based on the search results,",
            "According to the web search,"
        ]
        for phrase in phrases_to_strip:
            clean_output = clean_output.replace(phrase, "")
            
        clean_output = clean_output.strip()
        
        print(f"Agent: {clean_output}\n")
        messages.append(AIMessage(content=final_message.content))

    except Exception as e:
        print(f"Error: {e}\n")