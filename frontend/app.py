import requests
import streamlit as st
import uuid

# CONFIG
import streamlit as st

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

# UTILS
def genrate_thread_id():
    return str(uuid.uuid4())

def reset_chat():
    thread_id = genrate_thread_id()
    st.session_state['thread_id'] = thread_id
    st.session_state['message_history'] = []

    if st.session_state['user']:
        requests.post(
            f"{BACKEND_URL}/create-chat",
            json={
                "thread_id": thread_id,
                "user_id": st.session_state['user']
            }
        )

    st.rerun()

# SESSION INIT
if "user" not in st.session_state:
    st.session_state["user"] = None

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = genrate_thread_id()

if "auth_mode" not in st.session_state:
    st.session_state["auth_mode"] = "login"

if "show_login" not in st.session_state:
    st.session_state["show_login"] = False

# SIDEBAR
st.sidebar.title("NexChat")

if not st.session_state["user"]:
    if st.sidebar.button("🔐 Login / Signup", use_container_width=True):
        st.session_state["show_login"] = not st.session_state["show_login"]

    if st.session_state["show_login"]:
        with st.sidebar.expander("Authentication", expanded=True):

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Login", use_container_width=True,key="toggle_login"):
                    st.session_state["auth_mode"] = "login"
            with col2:
                if st.button("Signup", use_container_width=True,key="toggle_signup"):
                    st.session_state["auth_mode"] = "signup"

            email = st.text_input("Email")
            password = st.text_input("Password", type="password")

            # SIGNUP
            if st.session_state["auth_mode"] == "signup":
                confirm_password = st.text_input("Confirm Password", type="password")

                if st.button("Create Account", use_container_width=True,key="signup_submit"):
                    if password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        response = requests.post(
                            f"{BACKEND_URL}/signup",
                            json={"email": email, "password": password}
                        )
                        user_id = response.json().get("user_id")

                        if user_id:
                            st.session_state["user"] = user_id
                            st.toast("🎉 Account created!", icon="🎉")
                            st.rerun()
                        else:
                            st.error("User already exists")

            # LOGIN
            else:
                if st.button("Login", use_container_width=True,key="login_submit"):
                    response = requests.post(
                        f"{BACKEND_URL}/login",
                        json={"email": email, "password": password}
                    )
                    user_id = response.json().get("user_id")

                    if user_id:
                        st.session_state["user"] = user_id
                        st.session_state["show_login"] = False
                        st.toast("✅ Logged in!", icon="✅")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")

            if st.button("Cancel", use_container_width=True,key="cancel_auth"):
                st.session_state["show_login"] = False
                st.rerun()

else:
    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        st.session_state["user"] = None
        st.session_state["message_history"] = []
        st.toast("👋 Logged out", icon="👋")
        st.rerun()

st.sidebar.divider()

# NEW CHAT
if st.sidebar.button("➕ New Chat", use_container_width=True):
    reset_chat()

# CHAT LIST
if st.session_state["user"]:
    st.sidebar.header("My Conversations")

    response = requests.get(f"{BACKEND_URL}/chats/{st.session_state['user']}")
    chats = response.json()["chats"]

    for thread_id, title in chats:
        if st.sidebar.button(title, key=thread_id, use_container_width=True):
            st.session_state["thread_id"] = thread_id
            st.session_state["message_history"] = []
            st.rerun()
else:
    st.sidebar.info("💡 Login to save chat history")

# EMPTY STATE
if len(st.session_state["message_history"]) == 0:
    st.markdown("""
        <div style="
            display:flex;
            justify-content:center;
            align-items:center;
            height:60vh;
            color:#888;
            font-size:28px;
            opacity:0.6;
        ">
            💬 Start chatting...
        </div>
    """, unsafe_allow_html=True)

# DISPLAY CHAT
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# CHAT INPUT
user_input = st.chat_input("Type here")

if user_input:

    if not st.session_state["user"] and len(st.session_state["message_history"]) >= 2:
        st.toast("💬 Login to save your conversation!", icon="💡")

    if len(st.session_state["message_history"]) == 0 and st.session_state["user"]:
        requests.post(
            f"{BACKEND_URL}/create-chat",
            json={
                "thread_id": st.session_state["thread_id"],
                "user_id": st.session_state["user"]
            }
        )

        requests.post(
            f"{BACKEND_URL}/update-title",
            json={
                "thread_id": st.session_state["thread_id"],
                "user_id": st.session_state["user"]
            }
        )

    # USER MESSAGE
    st.session_state["message_history"].append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    # ASSISTANT RESPONSE
    with st.chat_message("assistant"):
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={
                "message": user_input,
                "thread_id": st.session_state["thread_id"]
            }
        )

        ai_message = response.json()["response"]
        st.markdown(ai_message)

    st.session_state["message_history"].append({
        "role": "assistant",
        "content": ai_message
    })

