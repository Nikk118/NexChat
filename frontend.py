import streamlit as st
from backend import chatbot
from langchain_core.messages import HumanMessage
import uuid
from auth import create_user, verify_user
from databaseHelper import get_chats, create_chat, update_title

# utility function
def genrate_thread_id():
    return str(uuid.uuid4())

def reset_chat():
    thread_id = genrate_thread_id()
    st.session_state['thread_id'] = thread_id
    st.session_state['message_history'] = []
    
    if st.session_state['user']:
        create_chat(thread_id, st.session_state['user'])
    
    st.rerun()

def load_conversation(thread_id):
    state = chatbot.get_state(
        config={'configurable': {'thread_id': thread_id}}
    )
    
    if not state or not state.values:
        return []
    
    return state.values.get('messages', [])

# session initialization
if "user" not in st.session_state:
    st.session_state["user"] = None

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = genrate_thread_id()

if 'show_login' not in st.session_state:
    st.session_state['show_login'] = False

# Sidebar
st.sidebar.title("chatbot")

# Login/Logout button at top
if not st.session_state["user"]:
    if st.sidebar.button("🔐 Login", use_container_width=True):
        st.session_state['show_login'] = not st.session_state['show_login']
    
    # Show login form when button is clicked
    if st.session_state['show_login']:
        with st.sidebar.expander("Login", expanded=True):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Login", use_container_width=True):
                    user_id = verify_user(email, password)
                    if user_id:
                        st.session_state["user"] = user_id
                        st.session_state['show_login'] = False
                        st.toast("✅ Logged in successfully!", icon="✅")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
            
            with col2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state['show_login'] = False
                    st.rerun()
else:
    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        st.session_state["user"] = None
        st.session_state['message_history'] = []
        st.toast("👋 Logged out", icon="👋")
        st.rerun()
st.sidebar.divider()

# New Chat button
if st.sidebar.button("➕ New Chat", use_container_width=True):
    reset_chat()

# Conversations (only show if logged in)
if st.session_state["user"]:
    st.sidebar.header("My Conversations")
    chats = get_chats(st.session_state["user"])
    
    for thread_id, title in chats:
        if st.sidebar.button(title, key=thread_id, use_container_width=True):
            st.session_state['thread_id'] = thread_id
            messages = load_conversation(thread_id)
            
            temp_messages = []
            for message in messages:
                if isinstance(message, HumanMessage):
                    role = 'user'
                else:
                    role = 'assistant'
                temp_messages.append({'role': role, 'content': message.content})
            
            st.session_state['message_history'] = temp_messages
            st.rerun()
else:
    st.sidebar.info("💡 Login to save chat history")
if len(st.session_state['message_history']) == 0:
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
# Display chat history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}

# Chat input
user_input = st.chat_input('Type here')

if user_input:
    # Prompt login after first message if not logged in
    if not st.session_state['user'] and len(st.session_state['message_history']) >= 2:
        st.toast("💬 Login to save your conversation!", icon="💡")
    
    if len(st.session_state['message_history']) == 0 and st.session_state['user']:
        create_chat(st.session_state['thread_id'], st.session_state["user"])
    
    if len(st.session_state['message_history']) == 0 and st.session_state['user']:
        update_title(st.session_state['thread_id'], user_input[:25])
    
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    
    with st.chat_message('user'):
        st.text(user_input)
    
    with st.chat_message('assistant'):
        ai_message = st.write_stream(
            message_chunk.content for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages'
            )
        )
    
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})