import bcrypt
from databaseHelper import get_conn

# 🔐 Signup
def create_user(email, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, password) VALUES (%s, %s)",
                (email, hashed.decode())
            )

# 🔐 Login
def verify_user(email, password):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, password FROM users WHERE email=%s",
                (email,)
            )
            user = cur.fetchone()

            if not user:
                return None

            user_id, stored_hash = user

            if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                return user_id

            return None