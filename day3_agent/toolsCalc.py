# from langchain.tools import tool


# @tool
# def calculator(expression: str) -> str:
#     """
#     Use ONLY when the user asks for a mathematical calculation.

#     Examples:
#     - 2+2
#     - 45*18
#     - 100/25

#     Never use this tool for:
#     - greetings
#     - conversations
#     - opinions
#     - explanations
#     - introductions
#     - small talk
#     """

#     print(f"\n[CALCULATOR TOOL CALLED] {expression}")

#     try:
#         result = eval(expression)
#         return str(result)

#     except Exception as e:
#         return f"Calculator Error: {e}"



# from langchain.tools import tool


# @tool
# def calculator(expression: str) -> str:
#     """
#     Performs mathematical calculations.

#     Use this tool whenever ANY arithmetic,
#     equation, percentage, or mathematical
#     expression appears in the user's request.

#     Always prefer this tool over mental math.
#     """

#     print("\n" + "=" * 50)
#     print("CALCULATOR TOOL EXECUTED")
#     print(f"Expression: {expression}")
#     print("=" * 50)

#     try:
#         result = eval(expression)

#         print(f"Result: {result}")
#         print("=" * 50 + "\n")

#         return str(result)

#     except Exception as e:
#         print(f"Calculator Error: {e}")
#         return f"Calculator Error: {e}"


import re
from langchain.tools import tool


@tool
def calculator(expression: str) -> str:
    """Performs mathematical calculations.

    Use this tool whenever ANY arithmetic, equation, percentage, or
    mathematical expression appears in the user's request.
    """
    # Clean the input string
    expr_clean = expression.strip().lower()

    # If the LLM passed dummy values like "null", "0", or just text, intercept it
    if expr_clean in ["null", "none", "", "0"] or not any(
        char in expr_clean for char in "0123456789+-*/%()"
    ):
        return "Error: No valid mathematical expression detected. Please answer the user's conversational question directly without a tool."

    print("\n" + "=" * 50)
    print("CALCULATOR TOOL EXECUTED")
    print(f"Expression: {expression}")
    print("=" * 50)

    try:
        result = eval(expression)
        print(f"Result: {result}")
        print("=" * 50 + "\n")
        return str(result)

    except Exception as e:
        print(f"Calculator Error: {e}")
        return f"Calculator Error: {e}"