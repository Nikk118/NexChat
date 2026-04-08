import bcrypt
from db import get_conn

# 🔐 Signup
def create_user(email, password):
    with get_conn() as conn:
        with conn.cursor() as cur:

            # ✅ check if user already exists
            cur.execute(
                "SELECT id FROM users WHERE email=%s",
                (email,)
            )
            existing = cur.fetchone()

            if existing:
                return None  # 🚨 important

            # ✅ hash password
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

            # ✅ insert user + return id
            cur.execute(
                "INSERT INTO users (email, password) VALUES (%s, %s) RETURNING id",
                (email, hashed.decode())
            )

            user_id = cur.fetchone()[0]
            conn.commit()

            return user_id
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