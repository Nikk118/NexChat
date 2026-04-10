import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from importlib import import_module

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Handle import (version compatibility)
try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ModuleNotFoundError:
    PostgresSaver = import_module("langgraph_checkpoint_postgres").PostgresSaver

from db import get_db_uri

load_dotenv()




llm = HuggingFaceEndpoint(
    repo_id="meta-llama/Llama-3.1-8B-Instruct",
    temperature=0.7,
    max_new_tokens=512,
)

llm = ChatHuggingFace(llm=llm)


# STATE
class chatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# NODE
def chat_node(state: chatState) -> chatState:
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


# GRAPH
graph = StateGraph(chatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)



# create context manager
_checkpoint_ctx = PostgresSaver.from_conn_string(get_db_uri())

# manually enter (this gives actual saver object)
checkpoint = _checkpoint_ctx.__enter__()

# setup tables
checkpoint.setup()



chatbot = graph.compile(checkpointer=checkpoint)