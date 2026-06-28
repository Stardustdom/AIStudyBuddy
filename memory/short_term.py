from collections import deque

class ShortTermMemory:
    def __init__(self, max_len=5):
        self.messages = deque(maxlen=max_len)

    def add(self, role, content):
        self.messages.append({
            "role": role,
            "content": content
        })

    def get(self):
        return list(self.messages)