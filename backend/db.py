import psycopg
import os
import time
from dotenv import load_dotenv

load_dotenv()


# CONFIG
def get_db_uri() -> str:
    db_uri = os.getenv("DATABASE_URL") or os.getenv("DB_URI")
    if not db_uri:
        raise RuntimeError("Missing database URL. Set DATABASE_URL or DB_URI.")
    return db_uri


# CONNECTION
def get_conn(*, autocommit: bool = False):
    conn = psycopg.connect(
        get_db_uri(),
        connect_timeout=5 
    )
    conn.autocommit = autocommit
    return conn



def safe_db_call(func, retries=2, delay=1):
    for attempt in range(retries):
        try:
            return func()
        except psycopg.Error as e:
            print(f"DB error (attempt {attempt+1}):", e)

            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise


# CHAT FUNCTIONS

def create_chat(thread_id, user_id=None):
    def _query():
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chats (thread_id, title, user_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (thread_id, "New Chat", user_id)
                )
    return safe_db_call(_query)


def get_chats(user_id):
    def _query():
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT thread_id, title
                    FROM chats
                    WHERE user_id=%s
                    ORDER BY created_at DESC
                    """,
                    (user_id,)
                )
                return cur.fetchall()
    return safe_db_call(_query)


def update_title(thread_id, title):
    def _query():
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE chats
                    SET title=%s
                    WHERE thread_id=%s
                    """,
                    (title, thread_id)
                )
    return safe_db_call(_query)