import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

DB_URI = os.getenv("DB_URI")

def get_conn():
    return psycopg.connect(DB_URI)


# 🔹 Chat functions
def create_chat(thread_id, user_id=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chats (thread_id, title, user_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (thread_id, "New Chat", user_id)
            )


def get_chats(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT thread_id, title FROM chats WHERE user_id=%s ORDER BY created_at DESC",
                (user_id,)
            )
            return cur.fetchall()


def update_title(thread_id, title):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE chats SET title=%s WHERE thread_id=%s",
                (title, thread_id)
            )