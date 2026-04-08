from fastapi import FastAPI
from pydantic import BaseModel
from chatbot import chatbot
from langchain_core.messages import HumanMessage
from fastapi.middleware.cors import CORSMiddleware

from auth import create_user, verify_user
from db import get_chats, create_chat, update_title

app = FastAPI()

# ✅ CORS (important)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# SCHEMAS
# ======================
class ChatRequest(BaseModel):
    message: str
    thread_id: str

class AuthRequest(BaseModel):
    email: str
    password: str

class CreateChatRequest(BaseModel):
    thread_id: str
    user_id: str

# ======================
# ROUTES
# ======================
@app.get("/")
def home():
    return {"message": "API is running"}

# 🔐 Signup
@app.post("/signup")
def signup(req: AuthRequest):
    user_id = create_user(req.email, req.password)
    return {"user_id": user_id}

# 🔐 Login
@app.post("/login")
def login(req: AuthRequest):
    user_id = verify_user(req.email, req.password)
    return {"user_id": user_id}

# 💬 Chat
@app.post("/chat")
def chat(req: ChatRequest):
    result = chatbot.invoke(
        {"messages": [HumanMessage(content=req.message)]},
        config={"configurable": {"thread_id": req.thread_id}}
    )

    # ✅ get last AI message
    last_message = result["messages"][-1]

    return {"response": last_message.content}
# 📜 Get chats
@app.get("/chats/{user_id}")
def chats(user_id: str):
    return {"chats": get_chats(user_id)}

# ➕ Create chat
@app.post("/create-chat")
def create_chat_api(req: CreateChatRequest):
    create_chat(req.thread_id, req.user_id)
    return {"status": "ok"}

# ✏️ Update title
@app.post("/update-title")
def update_chat_title(req: CreateChatRequest):
    update_title(req.thread_id, "New Chat")
    return {"status": "ok"}

