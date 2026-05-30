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

NAV_HINT = (
    "\n\n---\n"
    "Escribe *menu* para ver el menú\n"
    "Escribe *pedido* para hacer tu pedido\n"
    "Escribe *reservar* para reservar mesa\n"
    "Escribe *inicio* para volver al inicio\n"
    "Escribe *cancelar* para detener el proceso"
)
