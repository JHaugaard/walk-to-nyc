import os
from dotenv import load_dotenv

load_dotenv(".env.local")

DB_PATH = os.getenv("DB_PATH", "walk.db")
COOKIE_SECRET = os.getenv("COOKIE_SECRET", "dev-secret-change-in-prod")
COOKIE_NAME = "walk_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # ~1 year, outlives the app
DEV_MODE = COOKIE_SECRET == "dev-secret-change-in-prod"
