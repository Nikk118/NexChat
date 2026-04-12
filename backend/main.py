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


@app.api_route("/", methods=["GET", "HEAD"])
def home(request: Request):
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
async def chat(req: ChatRequest):
    run = trace(
        name="NexChat Request",
        metadata={"thread_id": req.thread_id},
        tags=[f"thread:{req.thread_id}"],
        inputs={"message": req.message},
    )
    run.__enter__()

    def generate():
        full_response = ""
        try:
            for chunk, metadata in stream_chatbot(
                {"messages": [HumanMessage(content=req.message)]},
                config={"configurable": {"thread_id": req.thread_id}},
                thread_id=req.thread_id,
            ):
                token = getattr(chunk, "content", "")
                if token:
                    full_response += token
                    yield json.dumps({"token": token}) + "\n"

            run.outputs = {"response": full_response}  # set outputs directly
            run.__exit__(None, None, None)             # this submits the trace
            yield json.dumps({"done": True}) + "\n"

        except Exception as exc:
            run.__exit__(type(exc), exc, exc.__traceback__)
            yield json.dumps({"done": True, "error": str(exc)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
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