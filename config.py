import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing in .env file")

if not ADMIN_ID:
    raise ValueError("ADMIN_ID is missing in .env file")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise ValueError("ADMIN_ID must be a valid number")


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

