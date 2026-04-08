# 🧠 EchoMind

**EchoMind** is a full-stack AI chatbot with persistent memory, authentication, and conversation management.
Built using **LangGraph, FastAPI, PostgreSQL, and Streamlit**, it delivers a stateful AI experience similar to modern AI assistants.

---

## 🚀 Features

* 🤖 AI-powered chatbot using HuggingFace LLM
* 🧠 Persistent memory with LangGraph + PostgreSQL
* 🔐 User authentication (Signup/Login)
* 💬 Multi-conversation support
* 📝 Automatic chat title generation
* ⚡ Real-time chat interface (Streamlit)
* 🌐 API-based architecture (Frontend ↔ Backend)

---

## 🏗️ Tech Stack

### Frontend

* Streamlit
* Requests

### Backend

* FastAPI
* LangGraph
* LangChain
* HuggingFace Inference API

### Database

* PostgreSQL

### Other

* Bcrypt (password hashing)
* Python-dotenv

---

## 📁 Project Structure

```
chatbot/
│
├── backend/
│   ├── main.py
│   ├── chatbot.py
│   ├── auth.py
│   ├── db.py
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── app.py
│   └── requirements.txt
│
├── .gitignore
└── README.md
```

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the repository

```bash
git clone <your-repo-url>
cd chatbot
```

---

### 2️⃣ Setup Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Create `.env` file:

```env
DATABASE_URL=your_postgres_url
HUGGINGFACEHUB_API_TOKEN=your_api_key
```

Run backend:

```bash
uvicorn main:app --reload
```

---

### 3️⃣ Setup Frontend

```bash
cd frontend
pip install -r requirements.txt
```

Update backend URL in `app.py`:

```python
BACKEND_URL = "http://localhost:8000"
```

Run frontend:

```bash
streamlit run app.py
```

---

## 🧪 API Endpoints

| Method | Endpoint           | Description        |
| ------ | ------------------ | ------------------ |
| POST   | `/signup`          | Create new user    |
| POST   | `/login`           | Authenticate user  |
| POST   | `/chat`            | Send message to AI |
| GET    | `/chats/{user_id}` | Get user chats     |
| POST   | `/create-chat`     | Create new chat    |
| POST   | `/update-title`    | Update chat title  |

---

## 🌍 Deployment

### Backend

* Deploy on **Render**
* Add environment variables:

  * `DATABASE_URL`
  * `HUGGINGFACEHUB_API_TOKEN`

### Frontend

* Deploy on **Streamlit Cloud**
* Update backend URL to deployed API

---

## ⚠️ Notes

* Ensure PostgreSQL database is running and accessible
* Do not commit `.env` file (use `.gitignore`)
* Use a clean `requirements.txt` for deployment

---

## 🔮 Future Improvements

* 🔄 Streaming responses (real-time typing effect)
* 🔐 JWT-based authentication
* 📊 Chat analytics
* 🎨 UI enhancements
* 🌍 Custom domain deployment

---

## 👨‍💻 Author

Built with ❤️ Nikk18

---

## ⭐ If you like this project

Give it a star ⭐ and share it!
