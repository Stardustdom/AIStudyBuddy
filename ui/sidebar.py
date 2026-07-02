import streamlit as st

from memory.chat_history import ChatHistory

history = ChatHistory()


def render_sidebar():

    with st.sidebar:

        st.title("📚 AI Study Buddy")

        st.divider()

        # ----------------------------
        # New Chat
        # ----------------------------

        if st.button("➕ New Chat", use_container_width=True):

            chat_id = history.create_chat()

            st.session_state.current_chat = chat_id

            st.rerun()

        st.divider()

        # ----------------------------
        # Search Chats
        # ----------------------------

        search = st.text_input(
            "🔍 Search Chats",
            placeholder="Search..."
        )

        chats = history.get_all_chats()

        if search:

            chats = {

                cid: chat

                for cid, chat in chats.items()

                if search.lower() in chat["title"].lower()

            }

        st.markdown("### Chats")

        # ----------------------------
        # Chat List
        # ----------------------------

        for chat_id, chat in chats.items():

            col1, col2, col3 = st.columns([6,1,1])

            with col1:

                if st.button(
                    chat["title"],
                    key=f"open_{chat_id}",
                    use_container_width=True
                ):

                    st.session_state.current_chat = chat_id

                    st.rerun()

            with col2:

                if st.button(
                    "✏",
                    key=f"rename_{chat_id}"
                ):

                    st.session_state.rename_chat = chat_id

            with col3:

                if st.button(
                    "🗑",
                    key=f"delete_{chat_id}"
                ):

                    history.delete_chat(chat_id)

                    if (
                        st.session_state.get("current_chat")
                        == chat_id
                    ):

                        st.session_state.current_chat = None

                    st.rerun()

        # ----------------------------
        # Rename Popup
        # ----------------------------

        if "rename_chat" in st.session_state:

            cid = st.session_state.rename_chat

            new_title = st.text_input(
                "Rename Chat",
                key="rename_input"
            )

            if st.button("Save"):

                if new_title.strip():

                    history.rename_chat(
                        cid,
                        new_title
                    )

                del st.session_state.rename_chat

                st.rerun()