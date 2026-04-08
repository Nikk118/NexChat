import os
import uuid

import requests
import streamlit as st


# CONFIG



BACKEND_URL = "https://nexchat-backend-6j4o.onrender.com"


# UTILS
def genrate_thread_id():
    return str(uuid.uuid4())


def make_chat_title(text: str) -> str:
    words = text.strip().split()
    title = " ".join(words[:6])
    return title if title else "New Chat"


def fetch_chat_history(thread_id: str):
    try:
        response = requests.get(f"{BACKEND_URL}/chat-history/{thread_id}", timeout=30)
        if response.status_code == 200:
            return response.json().get("messages", [])
    except Exception:
        pass
    return []


def persist_user_session(user_id: str):
    st.query_params["user"] = str(user_id)


def restore_user_session():
    user = st.query_params.get("user")
    return str(user) if user else None


def clear_persisted_user_session():
    if "user" in st.query_params:
        del st.query_params["user"]


def add_local_thread(thread_id: str, title: str = "New Chat"):
    if not any(t["id"] == thread_id for t in st.session_state["chat_threads"]):
        st.session_state["chat_threads"].append({"id": thread_id, "title": title})


def set_local_thread_title(thread_id: str, title: str):
    for thread in st.session_state["chat_threads"]:
        if thread["id"] == thread_id:
            thread["title"] = title
            return


def save_local_history(thread_id: str):
    st.session_state["thread_histories"][thread_id] = list(st.session_state["message_history"])


def load_local_history(thread_id: str):
    return list(st.session_state["thread_histories"].get(thread_id, []))


def reset_chat():
    thread_id = genrate_thread_id()
    st.session_state["thread_id"] = thread_id
    st.session_state["message_history"] = []
    add_local_thread(thread_id)
    save_local_history(thread_id)

    if st.session_state["user"]:
        try:
            requests.post(
                f"{BACKEND_URL}/create-chat",
                json={"thread_id": thread_id, "user_id": st.session_state["user"]},
                timeout=30,
            )
        except Exception:
            pass

    st.rerun()


# SESSION INIT
if "user" not in st.session_state:
    st.session_state["user"] = restore_user_session()

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = genrate_thread_id()

if "auth_mode" not in st.session_state:
    st.session_state["auth_mode"] = "login"

if "show_login" not in st.session_state:
    st.session_state["show_login"] = False

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = []

if "thread_histories" not in st.session_state:
    st.session_state["thread_histories"] = {}

add_local_thread(st.session_state["thread_id"])
save_local_history(st.session_state["thread_id"])


# SIDEBAR
st.sidebar.title("NexChat")



if not st.session_state["user"]:
    if st.sidebar.button("Login / Signup", use_container_width=True):
        st.session_state["show_login"] = not st.session_state["show_login"]

    if st.session_state["show_login"]:
        with st.sidebar.expander("Authentication", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Login", use_container_width=True, key="toggle_login"):
                    st.session_state["auth_mode"] = "login"
            with col2:
                if st.button("Signup", use_container_width=True, key="toggle_signup"):
                    st.session_state["auth_mode"] = "signup"

            email = st.text_input("Email")
            password = st.text_input("Password", type="password")

            if st.session_state["auth_mode"] == "signup":
                confirm_password = st.text_input("Confirm Password", type="password")

                if st.button("Create Account", use_container_width=True, key="signup_submit"):
                    if password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        response = requests.post(
                            f"{BACKEND_URL}/signup",
                            json={"email": email, "password": password},
                            timeout=30,
                        )
                        user_id = response.json().get("user_id")

                        if user_id:
                            st.session_state["user"] = str(user_id)
                            persist_user_session(str(user_id))
                            st.toast("Account created")
                            st.rerun()
                        else:
                            st.error("User already exists")
            else:
                if st.button("Login", use_container_width=True, key="login_submit"):
                    response = requests.post(
                        f"{BACKEND_URL}/login",
                        json={"email": email, "password": password},
                        timeout=30,
                    )
                    user_id = response.json().get("user_id")

                    if user_id:
                        st.session_state["user"] = str(user_id)
                        persist_user_session(str(user_id))
                        st.session_state["show_login"] = False
                        st.toast("Logged in")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")

            if st.button("Cancel", use_container_width=True, key="cancel_auth"):
                st.session_state["show_login"] = False
                st.rerun()
else:
    if st.sidebar.button("Sign Out", use_container_width=True):
        st.session_state["user"] = None
        clear_persisted_user_session()
        st.toast("Logged out")
        st.rerun()

st.sidebar.divider()

if st.sidebar.button("New Chat", use_container_width=True):
    reset_chat()


# CHAT LIST
st.sidebar.header("My Conversations")

sidebar_threads = []
if st.session_state["user"]:
    try:
        response = requests.get(f"{BACKEND_URL}/chats/{st.session_state['user']}", timeout=30)
        remote_threads = response.json().get("chats", []) if response.status_code == 200 else []
    except Exception:
        remote_threads = []

    sidebar_threads = [{"id": t_id, "title": title} for t_id, title in remote_threads]

    if not any(t["id"] == st.session_state["thread_id"] for t in sidebar_threads):
        local_current = next(
            (t for t in st.session_state["chat_threads"] if t["id"] == st.session_state["thread_id"]),
            {"id": st.session_state["thread_id"], "title": "New Chat"},
        )
        sidebar_threads.insert(0, local_current)
else:
    sidebar_threads = list(reversed(st.session_state["chat_threads"]))

conversation_panel = st.sidebar.container(height=420, border=False)
for thread in sidebar_threads:
    if conversation_panel.button(thread["title"], key=f"thread_{thread['id']}", use_container_width=True):
        st.session_state["thread_id"] = thread["id"]
        if st.session_state["user"]:
            history = fetch_chat_history(thread["id"])
            st.session_state["message_history"] = history if history else load_local_history(thread["id"])
        else:
            st.session_state["message_history"] = load_local_history(thread["id"])
        st.rerun()

if not st.session_state["user"]:
    st.sidebar.info("Login to save chats to database")


# EMPTY STATE
if len(st.session_state["message_history"]) == 0:
    st.markdown(
        """
        <div style="
            display:flex;
            justify-content:center;
            align-items:center;
            height:60vh;
            color:#888;
            font-size:28px;
            opacity:0.6;
        ">
            Start chatting...
        </div>
    """,
        unsafe_allow_html=True,
    )


# DISPLAY CHAT
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# CHAT INPUT
user_input = st.chat_input("Type here")

if user_input:
    add_local_thread(st.session_state["thread_id"])

    if len(st.session_state["message_history"]) == 0:
        title = make_chat_title(user_input)
        set_local_thread_title(st.session_state["thread_id"], title)

        if st.session_state["user"]:
            try:
                requests.post(
                    f"{BACKEND_URL}/create-chat",
                    json={"thread_id": st.session_state["thread_id"], "user_id": st.session_state["user"]},
                    timeout=30,
                )
                requests.post(
                    f"{BACKEND_URL}/update-title",
                    json={"thread_id": st.session_state["thread_id"], "title": title},
                    timeout=30,
                )
            except Exception:
                pass

    st.session_state["message_history"].append({"role": "user", "content": user_input})
    save_local_history(st.session_state["thread_id"])

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={"message": user_input, "thread_id": st.session_state["thread_id"]},
            timeout=60,
        )

        ai_message = response.json().get("response", "")
        st.markdown(ai_message)

    st.session_state["message_history"].append({"role": "assistant", "content": ai_message})
    save_local_history(st.session_state["thread_id"])

