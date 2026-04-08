from fastapi import FastAPI
from pydantic import BaseModel
from chatbot import chatbot
from langchain_core.messages import HumanMessage
from fastapi.middleware.cors import CORSMiddleware

from auth import create_user, verify_user
from db import get_chats, create_chat, update_title

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str


class AuthRequest(BaseModel):
    email: str
    password: str


class CreateChatRequest(BaseModel):
    thread_id: str
    user_id: str


class UpdateTitleRequest(BaseModel):
    thread_id: str
    title: str


@app.get("/")
def home():
    return {"message": "API is running"}


@app.post("/signup")
def signup(req: AuthRequest):
    user_id = create_user(req.email, req.password)
    return {"user_id": user_id}


@app.post("/login")
def login(req: AuthRequest):
    user_id = verify_user(req.email, req.password)
    return {"user_id": user_id}


@app.post("/chat")
def chat(req: ChatRequest):
    result = chatbot.invoke(
        {"messages": [HumanMessage(content=req.message)]},
        config={"configurable": {"thread_id": req.thread_id}},
    )

    last_message = result["messages"][-1]
    return {"response": last_message.content}


@app.get("/chat-history/{thread_id}")
def chat_history(thread_id: str):
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    values = getattr(state, "values", {}) or {}
    messages = values.get("messages", [])

    history = []
    for msg in messages:
        msg_type = getattr(msg, "type", "")
        role = "user" if msg_type == "human" else "assistant"
        content = getattr(msg, "content", "")
        if not isinstance(content, str):
            content = str(content)
        history.append({"role": role, "content": content})

    return {"messages": history}


@app.get("/chats/{user_id}")
def chats(user_id: str):
    return {"chats": get_chats(user_id)}


@app.post("/create-chat")
def create_chat_api(req: CreateChatRequest):
    create_chat(req.thread_id, req.user_id)
    return {"status": "ok"}


@app.post("/update-title")
def update_chat_title(req: UpdateTitleRequest):
    cleaned_title = req.title.strip() if req.title else ""
    update_title(req.thread_id, cleaned_title or "New Chat")
    return {"status": "ok"}
