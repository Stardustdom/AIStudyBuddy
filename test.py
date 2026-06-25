from ollama import chat

response = chat(
    model='mistral',
    messages=[
        {'role': 'user', 'content': 'whats your name!'}
    ]
)

print(response['message']['content'])