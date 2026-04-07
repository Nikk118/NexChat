import streamlit as st
from backend import chatbot
from langchain_core.messages import HumanMessage
import uuid


# uitlity function
def genrate_thread_id():
     return str(uuid.uuid4())

def reset_chat():
    thread_id = genrate_thread_id()

    st.session_state['thread_id'] = thread_id
    st.session_state['message_history'] = []

    add_thread(thread_id)

    st.rerun()

def add_thread(thread_id):
    if not any(t["id"] == thread_id for t in st.session_state['chat_threads']):
        st.session_state['chat_threads'].append({
            "id": thread_id,
            "title": "New Chat"
        })

def load_conversation(thread_id):
        state = chatbot.get_state(
        config={'configurable': {'thread_id': thread_id}}
    )

        if not state or not state.values:
                return []

        return state.values.get('messages', [])

# session

if 'chat_threads' not in st.session_state:
     st.session_state['chat_threads']=[]


if 'message_history' not in st.session_state:
     st.session_state['message_history']=[]

if 'thread_id' not in st.session_state:
     print("hello")
     st.session_state['thread_id']=genrate_thread_id()




# side bar
st.sidebar.title("chatbot")

if st.sidebar.button("New Chat"):
     reset_chat()

st.sidebar.header("My Conversations")
for thread in st.session_state['chat_threads'][::-1]:
        if st.sidebar.button(thread["title"], key=thread["id"]):
                st.session_state['thread_id']=thread["id"]
                messages=load_conversation(thread["id"])

                temp_messages=[]
                for message in messages:
                        if isinstance(message,HumanMessage):
                          role='user'
                        else:
                          role='assistant'
                        temp_messages.append({'role':role,'content':message.content})
                st.session_state['message_history']=temp_messages
                st.rerun()

for message in st.session_state['message_history']:
     with st.chat_message(message['role']):
        st.text(message['content'])

CONFIG={'configurable':{'thread_id':st.session_state['thread_id']}}

# ui
user_input=st.chat_input('Type here')


if user_input:
    add_thread(st.session_state['thread_id'])
    
            

    st.session_state['message_history'].append({'role':'user','content':user_input})
    with st.chat_message('user'):
            st.text(user_input)
    for thread in st.session_state['chat_threads']:
        if thread['id'] == st.session_state['thread_id'] and thread["title"] == "New Chat":
            thread['title'] = user_input[:25]
            

    with st.chat_message('assistant'):
        ai_message=st.write_stream(
             message_chunk.content for message_chunk,metadata in chatbot.stream(
                   {'messages':[HumanMessage(content=user_input)]},
    config=CONFIG,
    stream_mode='messages'
             )
        )
    st.session_state['message_history'].append({'role':'assistant','content':ai_message})

   
        
