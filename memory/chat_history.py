import json
import os
import uuid
from datetime import datetime


class ChatHistory:

    def __init__(self, filename=None):

        if filename is None:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )

            filename = os.path.join(
                base_dir,
                "memory",
                "chat_history.json"
            )

        self.filename = filename

        # Make sure the folder exists
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)

        # Create the JSON file if it doesn't exist
        if not os.path.exists(self.filename):
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4)

    # ------------------------------------
    # Internal helpers
    # ------------------------------------

    def _load(self):

        with open(self.filename, "r") as f:
            return json.load(f)

    def _save(self, data):

        with open(self.filename, "w") as f:
            json.dump(data, f, indent=4)

    # ------------------------------------
    # Chat operations
    # ------------------------------------

    def create_chat(self, title="New Chat"):

        data = self._load()

        chat_id = str(uuid.uuid4())

        data[chat_id] = {

            "title": title,

            "created_at": datetime.now().isoformat(),

            "messages": [],

            "topics": []

        }

        self._save(data)

        return chat_id

    def get_all_chats(self):

        return self._load()

    def rename_chat(self, chat_id, title):

        data = self._load()

        if chat_id in data:

            data[chat_id]["title"] = title

            self._save(data)

    def delete_chat(self, chat_id):

        data = self._load()

        if chat_id in data:

            del data[chat_id]

            self._save(data)

    # ------------------------------------
    # Messages
    # ------------------------------------

    def add_message(self, chat_id, role, content):

        data = self._load()

        data[chat_id]["messages"].append({

            "role": role,

            "content": content,

            "time": datetime.now().isoformat()

        })

        self._save(data)

    def get_messages(self, chat_id):

        data = self._load()

        return data[chat_id]["messages"]

    # ------------------------------------
    # Topics
    # ------------------------------------

    def add_topic(self, chat_id, topic_state):

        data = self._load()

        data[chat_id]["topics"].append(topic_state)

        self._save(data)

    def get_topics(self, chat_id):

        data = self._load()

        return data[chat_id]["topics"]

    # ------------------------------------
    # Quiz History
    # ------------------------------------

    def add_quiz(self, chat_id, topic_name, quiz_state):

        data = self._load()

        topics = data[chat_id]["topics"]

        for topic in topics:

            if topic["topic"] == topic_name:

                if "quiz_history" not in topic:

                    topic["quiz_history"] = []

                topic["quiz_history"].append(quiz_state)

                break

        self._save(data)

    # ------------------------------------
    # Chat State
    # ------------------------------------

    def save_state(self, chat_id, state):

        data = self._load()

        data[chat_id]["state"] = state

        self._save(data)

    def load_state(self, chat_id):

        data = self._load()

        if chat_id not in data:
            return {}

        return data[chat_id].get("state", {})