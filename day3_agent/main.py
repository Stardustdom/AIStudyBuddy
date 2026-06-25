# from langchain.agents import create_agent
# from langchain_ollama import ChatOllama

# from toolsCalc import calculator


# SYSTEM_PROMPT = """
# You are an AI assistant with access to calculator tools.
# NOTE:YOU NEED TO ACCESS THE TOOL WHENEVER THERE IS AN EXPRESSION YOU CANNOT DO CALCULATIONS ON YOUR OWN YOU HAVE TO PASS IT TO THE CALCULATOR TOOL.

# CRITICAL RULES:

# 1. Before answering ANY user message, determine whether it contains:

#    * a mathematical expression
#    * a calculation request
#    * arithmetic
#    * percentages
#    * equations
#    * algebraic expressions

# 2. If ANY calculation is required:

#    * You MUST use the calculator tool.
#    * You MUST NOT perform the calculation yourself.
#    * This rule applies even if the message also contains greetings, conversation, opinions, or multiple questions.

# 3. If no calculation is required:

#    * Do NOT use the calculator tool.
#    * Answer normally.

# OUTPUT FORMAT:

# For every response, use exactly this structure:

# THOUGHT: <one of the following>

# * NEEDS CALCULATOR
# * REGULAR CONVERSATION

# ACTION: <one of the following>

# * CALCULATOR TOOL
# * NO TOOL REQUIRED

# ANSWER: <final response>

# EXAMPLES

# User: Hello

# THOUGHT:
# REGULAR CONVERSATION

# ACTION:
# NO TOOL REQUIRED

# ANSWER:
# Hello! How can I help you today?

# User: What is 5*8?

# THOUGHT:
# NEEDS CALCULATOR

# ACTION:
# CALCULATOR TOOL

# ANSWER:
# The result is 40.

# User: My name is Megha. What is 8*9?

# THOUGHT:
# NEEDS CALCULATOR

# ACTION:
# CALCULATOR TOOL

# ANSWER:
# Hello Megha. The result is 72.

# Never skip this format.
# Never calculate manually when a calculator tool is available.



# """


# # LLM
# model = ChatOllama(
#     model="mistral",
#     temperature=0
# )


# # Agent
# agent = create_agent(
#     model=model,
#     tools=[calculator],
#     system_prompt=SYSTEM_PROMPT
# )


# # Conversation memory
# messages = []


# print("=== AI Study Buddy ===")
# print("Type 'exit' to quit.\n")


# while True:

#     user_input = input("You: ")

#     if user_input.lower() == "exit":
#         print("Goodbye!")
#         break

#     messages.append(
#         {
#             "role": "user",
#             "content": user_input
#         }
#     )

#     try:

#         response = agent.invoke(
#             {
#                 "messages": messages
#             }
#         )

#         assistant_message = response["messages"][-1]

#         print("\nAgent:")
#         print(assistant_message.content)

#         messages.append(
#             {
#                 "role": "assistant",
#                 "content": assistant_message.content
#             }
#         )

#     except Exception as e:

#         print(f"\nError: {e}")



# from langchain.agents import create_agent
# from langchain_ollama import ChatOllama

# from toolsCalc import calculator


# SYSTEM_PROMPT = """
# You are an AI assistant with access to tools.

# CRITICAL RULES:

# 1. Before answering ANY user message, determine whether it contains:
#    - a mathematical expression
#    - a calculation request
#    - arithmetic
#    - percentages
#    - equations
#    - algebraic expressions

# 2. If ANY calculation is required:
#    - You MUST use the calculator tool.
#    - You MUST NOT perform the calculation yourself.
#    - This rule applies even if the message also contains greetings,
#      conversation, opinions, or multiple questions.

# 3. If no calculation is required:
#    - Do NOT use the calculator tool.
#    - Answer normally.

# OUTPUT FORMAT:

# THOUGHT:
# <NEEDS CALCULATOR or REGULAR CONVERSATION>

# ACTION:
# <CALCULATOR TOOL or NO TOOL REQUIRED>

# ANSWER:
# <final response>

# EXAMPLES

# User: Hello

# THOUGHT:
# REGULAR CONVERSATION

# ACTION:
# NO TOOL REQUIRED

# ANSWER:
# Hello! How can I help you today?

# User: What is 5*8?

# THOUGHT:
# NEEDS CALCULATOR

# ACTION:
# CALCULATOR TOOL

# ANSWER:
# The result is 40.

# User: My name is Megha. What is 8*9?

# THOUGHT:
# NEEDS CALCULATOR

# ACTION:
# CALCULATOR TOOL

# ANSWER:
# Hello Megha. The result is 72.

# Never skip this format.

# Never calculate manually when a calculator tool is available.
# """


# # LLM
# model = ChatOllama(
#     model="llama3.1:8b",
#     temperature=0
# )


# # Agent
# agent = create_agent(
#     model=model,
#     tools=[calculator],
#     system_prompt=SYSTEM_PROMPT
# )


# # Memory
# messages = []


# print("=== AI Study Buddy ===")
# print("Type 'exit' to quit.\n")


# while True:

#     user_input = input("You: ")

#     if user_input.lower() == "exit":
#         print("Goodbye!")
#         break

#     messages.append(
#         {
#             "role": "user",
#             "content": user_input
#         }
#     )

#     try:

#         print("\nProcessing...\n")

#         response = agent.invoke(
#             {
#                 "messages": messages
#             }
#         )

#         assistant_message = response["messages"][-1]

#         print("Agent:")
#         print(assistant_message.content)

#         messages.append(
#             {
#                 "role": "assistant",
#                 "content": assistant_message.content
#             }
#         )

#     except Exception as e:

#         print(f"\nError: {e}")


from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama

from toolsCalc import calculator

# We must be explicitly strict about mathematical data integrity
SYSTEM_PROMPT = """
You are a helpful, straight-forward AI Study Buddy who uses CALCULATOR TOOL ONLY WHEN THERE IS AN EXPRESSION.

!!!!!!DONT INSERT INTERNAL THOUGHTS IN YOUR ANSWER!!!!!!

CRITICAL RULES:
1. Always check if the user request requires mathematical calculations or arithmetic. ONLY use the calculator tool if the user's message contains explicit numbers AND mathematical operators (like +, -, *, /, or percentages).
2. If it does, you MUST use the calculator tool. NEVER compute answers yourself.
3. If no calculation is needed, respond naturally like a human friend.

HYBRID REQUEST HANDLING (CRITICAL):
- If a user sends a message containing BOTH conversation (e.g., "Hello, how are you?") AND a math calculation (e.g., "What is 2+2?"), your final response MUST address both components.
- Greet or respond to the conversational part naturally first, and then seamlessly integrate the exact mathematical result returned by the tool.

CONVERSATION STYLE:
- Talk directly to the user. 
- NEVER output internal thoughts or robotic prefixes like "No calculation is required", "The result of the calculation is", or "The answer to your question is".
- Always use the EXACT number string returned by the tool. Never alter, round, or hallucinate the math results.
"""

# Initialize LLM
model = ChatOllama(model="llama3.1:8b", temperature=0)

# Build the agent
agent = create_agent(
    model=model,
    tools=[calculator],
    system_prompt=SYSTEM_PROMPT
)

messages = []

print("=== AI Study Buddy ===")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        print("Goodbye!")
        break

    print("\nProcessing...\n")
    messages.append(HumanMessage(content=user_input))

    try:
        response = agent.invoke({"messages": messages})
        final_message = response["messages"][-1]
        
        # --- Python Sanitization (Bulletproof Fallback) ---
        clean_output = final_message.content
        
        # Strip away common annoying meta-phrases if the LLM slips up
        phrases_to_strip = [
            "No calculation is required to answer your question. I'll just respond normally.",
            "However, I can still respond naturally like a human friend",
            "No calculation is required for your greeting.",
            "No calculation is required for your response.",
            "No calculation is required for your question.",
            "No calculation is required to answer your question.",
            "There is no calculation needed for your question.",
            "The result of the calculation is",
            "As for the calculation,"
        ]
        for phrase in phrases_to_strip:
            clean_output = clean_output.replace(phrase, "")
            
        clean_output = clean_output.strip()
        
        # Print the cleaned, natural response
        print(f"Agent: {clean_output}\n")
        
        messages.append(AIMessage(content=final_message.content))

    except Exception as e:
        print(f"\nError: {e}\n")

