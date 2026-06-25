import re
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from searchtool import web_search

# 1. System Prompt with strict constraints against internal reasoning leakage
SYSTEM_PROMPT = """You are a helpful AI assistant. 

You must choose between two internal modes based on the user's input:
1. CHAT MODE: For greetings (e.g., hello, hi), casual conversation, or pleasantries. Respond naturally from your internal knowledge. DO NOT call any tools.
2. SEARCH MODE: ONLY for factual queries, tutorials, news, or current events that require external data.

CRITICAL EXECUTION RULES:
- NEVER mention "modes", "CHAT MODE", or "SEARCH MODE" in your response. 
- NEVER explain your reasoning or why you chose to use or not use a tool.
- Do not output mock JSON, example tool calls, or function signatures to the user.
- Simply provide the direct, natural response to the user's input."""

# 2. Initialize the LLM and the Agent
model = ChatOllama(
    model="llama3.1:8b",
    temperature=0
)

agent = create_agent(
    model=model,
    tools=[web_search],
    system_prompt=SYSTEM_PROMPT
)

messages = []

# 3. Code-level bypass for greetings and short conversational triggers
CONVERSATIONAL_BYPASS = {
    "hello", "hi", "hey", "how are you", "how're you", 
    "good morning", "good afternoon", "good evening",
    "whats up", "what's up", "yo", "thank you", "thanks", 
    "no", "yes", "ok", "okay", "bye", "sure", "cool", "got it"
}

while True:
    user_input = input("\nYou: ")

    if user_input.lower() == "exit":
        break

    # Strip punctuation and normalize spacing
    cleaned_input = re.sub(r'[^\w\s]', '', user_input.strip().lower())
    
    # Catch both explicit bypass words AND ultra-short 1-word inputs (like "k", "y", "ya")
    if cleaned_input in CONVERSATIONAL_BYPASS or len(cleaned_input.split()) <= 1 and len(cleaned_input) < 4:
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
            
        print("\nAgent:")
        print(reply)
        
        messages.append({"role": "user", "content": user_input})
        messages.append({"role": "assistant", "content": reply})
        continue

    # 5. Let the LangChain agent execute complex, search-requiring inputs
    messages.append({"role": "user", "content": user_input})

    response = agent.invoke({"messages": messages})
    assistant_message = response["messages"][-1]

    print("\nAgent:")
    print(assistant_message.content)

    messages.append({"role": "assistant", "content": assistant_message.content})