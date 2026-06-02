import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
_loaded_from_files: set[str] = set()


def _load_env_file(path: Path, *, override_loaded: bool = False) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key in os.environ and key not in _loaded_from_files:
            # Respect real process env vars (Render/Railway, shell export, etc).
            continue
        if key in _loaded_from_files and not override_loaded:
            continue
        os.environ[key] = value
        _loaded_from_files.add(key)


_load_env_file(BASE_DIR / ".env.unified", override_loaded=False)
_load_env_file(BASE_DIR / ".env", override_loaded=True)
load_dotenv(BASE_DIR / ".env", override=False)

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

PARSER_ERROR_LOG_PATH = os.getenv(
    "PARSER_ERROR_LOG_PATH",
    str(BASE_DIR / "data" / "parser_errors.jsonl"),
)

ADMIN_REMINDER_INTERVAL_SECONDS = int(os.getenv("ADMIN_REMINDER_INTERVAL_SECONDS", "300"))
ADMIN_REMINDER_MAX_SECONDS = int(os.getenv("ADMIN_REMINDER_MAX_SECONDS", "3600"))

MENU_CACHE_TTL_SECONDS = int(os.getenv("MENU_CACHE_TTL_SECONDS", "60"))
ORDERS_CACHE_TTL_SECONDS = int(os.getenv("ORDERS_CACHE_TTL_SECONDS", "30"))

NAV_HINT = (
    "\n\n---\n"
    "Escribe *inicio* para volver al inicio\n"
)
