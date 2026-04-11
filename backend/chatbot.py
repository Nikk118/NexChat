import os
import threading
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from importlib import import_module
from langsmith import traceable
import psycopg
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

llm = ChatHuggingFace(llm=llm).with_config({
    "run_name":"LLm model",
    "metadata":{
        "model":"llma-3.1-8B-instruct"
    }
})


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

_chatbot_lock = threading.Lock()
_checkpoint_ctx = None
_chatbot = None


def _build_chatbot():
    checkpoint_ctx = PostgresSaver.from_conn_string(get_db_uri())
    checkpoint = checkpoint_ctx.__enter__()
    checkpoint.setup()
    compiled_graph = graph.compile(checkpointer=checkpoint)
    return compiled_graph, checkpoint_ctx


def _close_checkpoint():
    global _checkpoint_ctx
    if _checkpoint_ctx is not None:
        try:
            _checkpoint_ctx.__exit__(None, None, None)
        except Exception:
            # Swallow close failures because reconnect path should keep serving traffic.
            pass
        _checkpoint_ctx = None


def _ensure_chatbot():
    global _chatbot, _checkpoint_ctx
    with _chatbot_lock:
        if _chatbot is None:
            _chatbot, _checkpoint_ctx = _build_chatbot()
        return _chatbot


def _reset_chatbot():
    global _chatbot, _checkpoint_ctx
    with _chatbot_lock:
        _close_checkpoint()
        _chatbot, _checkpoint_ctx = _build_chatbot()


def _is_psycopg_error(exc: Exception) -> bool:
    current = exc
    while current:
        if isinstance(current, psycopg.Error):
            return True
        current = current.__cause__ or current.__context__
    return False

@traceable(name="NexChat Request")
def invoke_chatbot(payload, config,thread_id: str, retries: int = 1):
    for attempt in range(retries + 1):
        bot = _ensure_chatbot()
        try:
            return bot.invoke(payload,
                config=config)
        except Exception as exc:
            if attempt < retries and _is_psycopg_error(exc):
                _reset_chatbot()
                continue
            raise


def get_chatbot_state(config, retries: int = 1):
    for attempt in range(retries + 1):
        bot = _ensure_chatbot()
        try:
            return bot.get_state(config=config)
        except Exception as exc:
            if attempt < retries and _is_psycopg_error(exc):
                _reset_chatbot()
                continue
            raise
