import streamlit as st
from memory.chat_history import ChatHistory

history = ChatHistory()


def render_sidebar():

    with st.sidebar:

        st.title("📚 AI Study Buddy")

        st.divider()

        # ==========================================
        # New Chat
        # ==========================================

        if st.button(
            "➕ New Chat",
            use_container_width=True
        ):

            chat_id = history.create_chat()

            st.session_state.current_chat = chat_id
            st.session_state.selected_workspace = None
            st.session_state.loaded_chat = None

            st.rerun()

        st.divider()

        # ==========================================
        # Search
        # ==========================================

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

        st.markdown("### 💬 Chats")

        # ==========================================
        # Chat List
        # ==========================================

        for chat_id, chat in chats.items():

            with st.container(border=True):

                if st.button(
                    chat["title"],
                    key=f"open_{chat_id}",
                    use_container_width=True
                ):

                    st.session_state.current_chat = chat_id
                    st.session_state.selected_workspace = None
                    st.session_state.loaded_chat = None
                    st.rerun()

                c1, c2 = st.columns(2)

                with c1:

                    if st.button(
                        "✏ Rename",
                        key=f"rename_{chat_id}",
                        use_container_width=True
                    ):

                        st.session_state.rename_chat = chat_id

                with c2:

                    if st.button(
                        "🗑 Delete",
                        key=f"delete_{chat_id}",
                        use_container_width=True
                    ):

                        history.delete_chat(chat_id)

                        if (
                            "rename_chat" in st.session_state
                            and st.session_state.rename_chat == chat_id
                        ):
                            del st.session_state["rename_chat"]

                        chats_after = history.get_all_chats()

                        if st.session_state.current_chat == chat_id:

                            if chats_after:

                                st.session_state.current_chat = next(
                                    iter(chats_after)
                                )

                            else:

                                st.session_state.current_chat = history.create_chat()

                            st.session_state.messages = []
                            st.session_state.workspace = []
                            st.session_state.selected_workspace = None
                            st.session_state.loaded_chat = None

                        st.rerun()

        # ==========================================
        # Rename
        # ==========================================

        if "rename_chat" in st.session_state:

            st.divider()

            cid = st.session_state.rename_chat

            chats = history.get_all_chats()

            if cid not in chats:

                del st.session_state["rename_chat"]
                st.rerun()

            st.markdown("### ✏ Rename Chat")

            new_title = st.text_input(
                "Title",
                value=chats[cid]["title"],
                key="rename_input"
            )

            c1, c2 = st.columns(2)

            with c1:

                if st.button(
                    "Save",
                    use_container_width=True
                ):

                    if new_title.strip():

                        history.rename_chat(
                            cid,
                            new_title.strip()
                        )

                    del st.session_state["rename_chat"]

                    st.rerun()

            with c2:

                if st.button(
                    "Cancel",
                    use_container_width=True
                ):

                    del st.session_state["rename_chat"]

                    st.rerun()

        # ==========================================
        # Workspace
        # ==========================================

        st.divider()

        st.markdown("### 📚 Study Workspace")

        if not st.session_state.workspace:

            st.caption("No study topics yet.")

        else:

            for idx, item in enumerate(st.session_state.workspace):

                topic = item.get(
                    "topic",
                    f"Topic {idx+1}"
                )

                if st.button(
                    f"📘 {topic}",
                    key=f"workspace_{idx}",
                    use_container_width=True
                ):

                    st.session_state.selected_workspace = idx

                    st.rerun()