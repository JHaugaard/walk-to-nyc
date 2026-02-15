"""One-time script: create schema and seed 3 users with generated tokens.

Run once at initial deploy:
    python init_db.py

Prints raw tokens to stdout — the only time they are visible.
"""
import secrets
from db import get_db, init_schema
from auth import hash_token

SEED_USERS = [
    ("Sara", "walker", "short blonde hair"),
    ("Mariah", "walker", "chin-length brown hair"),
    ("Admin", "admin", None),
]


def seed_users():
    init_schema()
    db = get_db()

    existing = db.execute("SELECT COUNT(*) FROM user").fetchone()[0]
    if existing > 0:
        print("Users already exist. Skipping seed.")
        db.close()
        return

    print("Seeding users...\n")
    for name, role, emoji in SEED_USERS:
        raw_token = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO user (name, role, token_hash, emoji_descriptor) VALUES (?, ?, ?, ?)",
            (name, role, hash_token(raw_token), emoji),
        )
        print(f"  {name} ({role})")
        print(f"  Token: {raw_token}")
        print()

    db.commit()
    db.close()
    print("Done. Save these tokens — they will not be shown again.")


if __name__ == "__main__":
    seed_users()
