import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

RESTAURANT_NAME = os.getenv("RESTAURANT_NAME", "La Casa del Sabor")
GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv(
    "GOOGLE_SHEETS_CREDENTIALS_PATH",
    str(BASE_DIR / "credentials" / "google-service-account.json"),
)
GOOGLE_SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID", "")
STATE_PERSIST_PATH = os.getenv(
    "STATE_PERSIST_PATH",
    str(BASE_DIR / "data" / "user_states.json"),
)
FLOWS_PATH = BASE_DIR / "flows" / "restaurant_flow.json"

GLOBAL_COMMANDS = frozenset({"menu", "pedido", "reservar", "inicio", "cancelar"})

ADMIN_WHATSAPP_NUMBER = os.getenv("ADMIN_WHATSAPP_NUMBER", "").strip()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "").strip()

# Twilio shared sandbox number (not valid for production alerts).
TWILIO_WHATSAPP_SANDBOX_NUMBER = "+14155238886"


def is_twilio_whatsapp_sandbox() -> bool:
    from_digits = "".join(ch for ch in TWILIO_WHATSAPP_FROM if ch.isdigit())
    sandbox_digits = TWILIO_WHATSAPP_SANDBOX_NUMBER.lstrip("+")
    return sandbox_digits in from_digits or from_digits.endswith(sandbox_digits)

PARSER_ERROR_LOG_PATH = os.getenv(
    "PARSER_ERROR_LOG_PATH",
    str(BASE_DIR / "data" / "parser_errors.jsonl"),
)

ADMIN_REMINDER_INTERVAL_SECONDS = int(os.getenv("ADMIN_REMINDER_INTERVAL_SECONDS", "300"))
ADMIN_REMINDER_MAX_SECONDS = int(os.getenv("ADMIN_REMINDER_MAX_SECONDS", "3600"))

MENU_CACHE_TTL_SECONDS = int(os.getenv("MENU_CACHE_TTL_SECONDS", "60"))
ORDERS_CACHE_TTL_SECONDS = int(os.getenv("ORDERS_CACHE_TTL_SECONDS", "30"))
BLOCKED_USERS_CACHE_TTL_SECONDS = int(os.getenv("BLOCKED_USERS_CACHE_TTL_SECONDS", "15"))

# Incremental Sheets refresh (activates when row count >= threshold)
SHEETS_INCREMENTAL_THRESHOLD = int(os.getenv("SHEETS_INCREMENTAL_THRESHOLD", "500"))
SHEETS_FULL_REFRESH_INTERVAL_SECONDS = int(
    os.getenv("SHEETS_FULL_REFRESH_INTERVAL_SECONDS", "3600")
)
SHEETS_INCREMENTAL_BATCH_SIZE = int(os.getenv("SHEETS_INCREMENTAL_BATCH_SIZE", "100"))

NAV_HINT = (
    "\n\n---\n"
    "Escribe *inicio* para volver al inicio\n"
)
