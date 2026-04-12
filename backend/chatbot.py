import os
import threading
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from importlib import import_module
from langsmith import traceable
import psycopg
from PyPDF2 import PdfReader
from langchain_core.messages import SystemMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_mistralai import ChatMistralAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode,tools_condition
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
VECTOR_PATH = "vector_store"
os.makedirs(VECTOR_PATH, exist_ok=True)
VECTOR_DB=None
CURRENT_THREAD_ID = None

def extract_text_from_pdf(file_path:str)->str:
    reader=PdfReader(file_path)
    text=""
    for page in reader.pages:
        text+=page.extract_text() or ""
    return text

embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

def handle_pdf_upload(file_path: str):
    global VECTOR_DB

    print("📄 Processing PDF...")

    # if embeddings already exist → load instead of recompute
    if os.path.exists(os.path.join(VECTOR_PATH, "index.faiss")):
        print("⚡ Loading existing embeddings...")

        vectorstore = FAISS.load_local(
            VECTOR_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )

        VECTOR_DB = vectorstore.as_retriever(search_kwargs={"k": 3})

    else:
        VECTOR_DB = process_pdf(file_path)

    print("✅ PDF ready")


def process_pdf(file_path: str):
    text = extract_text_from_pdf(file_path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    chunks = splitter.create_documents([text])

    vectorstore = FAISS.from_documents(chunks, embeddings)

    # 🔥 SAVE EMBEDDINGS
    vectorstore.save_local(VECTOR_PATH)

    return vectorstore.as_retriever(search_kwargs={"k": 3})
@tool
def pdf_rag(query: str) -> str:
    """Use this tool ONLY when the user asks questions about the uploaded PDF document, 
its content, summary, or specific details. 

Do NOT use this tool for general knowledge, casual conversation, or questions that 
can be answered without referring to the uploaded document."""
    global VECTOR_DB

    if VECTOR_DB is None:
        return "No PDF uploaded."

    print(f"📄 RAG tool: {query}")

    docs = VECTOR_DB.invoke(query)

    return "\n".join([doc.page_content for doc in docs])

@tool
def calculator(expression: str) -> str:
    """Use this for math calculations like 2+2, 5*10, etc."""
    try:
        return str(eval(expression))
    except:
        return "Invalid expression"


    
search=DuckDuckGoSearchRun()

@tool
def duckduckgo_search(query: str) -> str:
    """Use this for real-time information, news, or unknown facts."""
    return search.run(query)

@tool
def weather(city: str) -> str:
    """Use this tool to get current weather or temperature of any city."""
    try:
        query = f"current temperature in {city}"
        print(f"🌦️ Weather tool called: {query}")

        result = search.run(query)
        return result

    except Exception as e:
        return "Unable to fetch weather right now"

BASE_TOOLS = [calculator, duckduckgo_search, weather]

tool_node = ToolNode(BASE_TOOLS)


# STATE
class chatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# NODE (keep simple)

from langchain_core.messages import AIMessage

def chat_node(state: chatState) -> chatState:
    messages = state["messages"]
    user_msg = messages[-1].content.lower()

    global VECTOR_DB

    # 🔥 KEYWORDS for document queries
    doc_keywords = [
        "pdf", "document", "file", "page",
        "summary", "summarize", "content", "explain"
    ]

    use_rag = VECTOR_DB is not None and any(k in user_msg for k in doc_keywords)

    # 🔥 FAST RAG PATH (no LLM decision)
    if use_rag:
        print("⚡ Direct RAG (fast)")

        docs = VECTOR_DB.invoke(user_msg)

        if not docs:
            return {"messages": [AIMessage(content="No relevant info found in document")]}

        return {
            "messages": [
                AIMessage(content="📄 From document:\n" + "\n".join([d.page_content for d in docs]))
            ]
        }

    # 🔥 NORMAL CHAT (FAST)
    print("⚡ Normal chat")

    dynamic_llm = llm.bind_tools(BASE_TOOLS)

    system_prompt = """
You are a helpful AI assistant.

- Answer general questions normally.
- Use tools only when necessary.
- Do NOT use any document tool unless explicitly needed.
"""

    messages = [SystemMessage(content=system_prompt)] + messages

    response = dynamic_llm.invoke(messages)

    return {"messages": [response]}
# GRAPH
graph = StateGraph(chatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools",tool_node)
graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node",tools_condition,{
    "tools":"tools",
    "__end__":END
})
graph.add_edge("tools","chat_node")

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