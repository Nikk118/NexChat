import os
import threading
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from importlib import import_module
from langsmith import traceable
import psycopg
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_mistralai import ChatMistralAI

# Handle import (version compatibility)
try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ModuleNotFoundError:
    PostgresSaver = import_module("langgraph_checkpoint_postgres").PostgresSaver

from db import get_db_uri

load_dotenv()

# ✅ ENABLE STREAMING
llm = ChatMistralAI(
    model="mistral-small",
    temperature=0.7,
    api_key=os.getenv("MISTRAL_API_KEY"),
    streaming=True
).with_config({
    "run_name": "LLM model",
    "metadata": {
        "model": "mistral-small"
    }
})


# STATE
class chatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# NODE (keep simple)
def chat_node(state: chatState) -> chatState:
    messages = state["messages"]
    response = llm.invoke(messages)  # LangGraph handles stream separately
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
            pass


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
def stream_chatbot(payload, config, thread_id: str, retries: int = 1):
    for attempt in range(retries + 1):
        bot = _ensure_chatbot()
        try:
            for chunk, metadata in bot.stream(
                payload,
                config=config,
                stream_mode="messages",
            ):
                yield chunk, metadata
            return
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