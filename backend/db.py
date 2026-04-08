import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_uri() -> str:
    # Render and most PaaS providers expose DATABASE_URL.
    db_uri = os.getenv("DATABASE_URL") or os.getenv("DB_URI")
    if not db_uri:
        raise RuntimeError("Missing database URL. Set DATABASE_URL (preferred) or DB_URI.")
    return db_uri

def get_conn(*, autocommit: bool = False):
    conn = psycopg.connect(get_db_uri())
    conn.autocommit = autocommit
    return conn


# Chat functions
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


