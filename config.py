import os
from pathlib import Path
from dotenv import load_dotenv

_env_file = Path(".env.local")
if _env_file.exists():
    load_dotenv(_env_file)

DB_PATH = os.getenv("DB_PATH", "walk.db")
COOKIE_SECRET = os.getenv("COOKIE_SECRET", "dev-secret-change-in-prod")
COOKIE_NAME = "walk_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # ~1 year, outlives the app
DEV_MODE = COOKIE_SECRET == "dev-secret-change-in-prod"
