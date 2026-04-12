from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from chatbot import get_chatbot_state, stream_chatbot
from langchain_core.messages import HumanMessage
from fastapi.middleware.cors import CORSMiddleware
from auth import create_user, verify_user
from db import get_chats, create_chat as db_create_chat, update_title
from fastapi import Request
from langsmith.run_helpers import trace
import json
from fastapi import UploadFile, File
import shutil
import os
from chatbot import handle_pdf_upload

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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


@app.api_route("/", methods=["GET", "HEAD"])
def home(request: Request):
    return {"message": "API is running"}


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # validate file
        if not file.filename.endswith(".pdf"):
            return {"error": "Only PDF files are allowed"}

        file_path = os.path.join(UPLOAD_DIR, file.filename)

        # save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # process for RAG
        handle_pdf_upload(file_path)

        return {"status": "PDF uploaded successfully"}

    except Exception as e:
        return {"error": str(e)}

@app.post("/chat")
async def chat(req: ChatRequest):

    def generate():
        try:
            for chunk, metadata in stream_chatbot(
                {"messages": [HumanMessage(content=req.message)]},
                config={"configurable": {"thread_id": req.thread_id}},
                thread_id=req.thread_id,
            ):
                token = getattr(chunk, "content", "")
                if token:
                    # ✅ Plain streaming (Render-friendly)
                    yield token

        except Exception as exc:
            yield f"\n[ERROR]: {str(exc)}"

    return StreamingResponse(
        generate(),
        media_type="text/plain",  # ✅ FIXED
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ===== OTHER ROUTES (UNCHANGED) =====

@app.post("/signup")
def signup(req: AuthRequest):
    user_id = create_user(req.email, req.password)
    return {"user_id": user_id}


@app.post("/login")
def login(req: AuthRequest):
    user_id = verify_user(req.email, req.password)
    return {"user_id": user_id}


@app.get("/chat-history/{thread_id}")
def chat_history(thread_id: str):
    state = get_chatbot_state(config={"configurable": {"thread_id": thread_id}})
    values = getattr(state, "values", {}) or {}
    messages = values.get("messages", [])

    history = []
    for msg in messages:
        msg_type = getattr(msg, "type", "")

        if msg_type not in ("human", "ai"):
            continue

        content = getattr(msg, "content", "")

        if isinstance(content, list):
            content = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        elif not isinstance(content, str):
            content = str(content)

        if not content.strip():
            continue

        role = "user" if msg_type == "human" else "assistant"
        history.append({"role": role, "content": content})

    return {"messages": history}


@app.get("/chats/{user_id}")
def chats(user_id: str):
    return {"chats": get_chats(user_id)}


@app.post("/create-chat")
def create_chat_api(req: CreateChatRequest):
    db_create_chat(req.thread_id, req.user_id)
    return {"status": "ok"}


@app.post("/update-title")
def update_chat_title(req: UpdateTitleRequest):
    cleaned_title = req.title.strip() if req.title else ""
    update_title(req.thread_id, cleaned_title or "New Chat")
    return {"status": "ok"}