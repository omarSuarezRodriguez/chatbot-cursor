"""Flask application and Twilio WhatsApp webhook."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import (  # noqa: E402
    GOOGLE_SHEETS_CREDENTIALS_PATH,
    GOOGLE_SPREADSHEET_ID,
    RESTAURANT_NAME,
    STATE_PERSIST_PATH,
)
from app.core.flow_engine import FlowEngine  # noqa: E402
from app.core.state_manager import StateManager  # noqa: E402
from app.integrations.google_sheets import GoogleSheetsClient  # noqa: E402
from app.services.menu_service import MenuService  # noqa: E402
from app.services.order_service import OrderService  # noqa: E402
from app.services.reservation_service import ReservationService  # noqa: E402
from app.services.user_service import UserService  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    flask_app = Flask(__name__)

    sheets_client = GoogleSheetsClient(
        credentials_path=GOOGLE_SHEETS_CREDENTIALS_PATH,
        spreadsheet_id=GOOGLE_SPREADSHEET_ID,
    )
    state_manager = StateManager(persist_path=STATE_PERSIST_PATH)
    menu_service = MenuService(sheets_client)
    order_service = OrderService(sheets_client, menu_service)
    reservation_service = ReservationService(sheets_client)
    user_service = UserService(sheets_client)
    flow_engine = FlowEngine(
        state_manager=state_manager,
        menu_service=menu_service,
        order_service=order_service,
        reservation_service=reservation_service,
    )

    flask_app.config["flow_engine"] = flow_engine
    flask_app.config["user_service"] = user_service

    @flask_app.get("/health")
    def health():
        return {
            "status": "ok",
            "service": "restaurant-chatbot",
            "restaurant": RESTAURANT_NAME,
        }

    @flask_app.post("/bot")
    def bot_webhook():
        response = MessagingResponse()
        wa_id = request.form.get("WaId") or ""
        profile_name = request.form.get("ProfileName", "")
        body = request.form.get("Body", "")

        if not wa_id:
            from_number = request.form.get("From", "")
            wa_id = from_number.replace("whatsapp:", "").strip()

        if not wa_id:
            response.message(
                "No pude identificar tu número. Intenta escribirnos de nuevo."
            )
            return str(response), 200, {"Content-Type": "application/xml"}

        try:
            user_service.touch(wa_id=wa_id, name=profile_name)
            reply = flow_engine.process_message(wa_id=wa_id, body=body)
        except Exception:
            logger.exception("Error processing message for wa_id=%s", wa_id)
            reply = (
                "Disculpa, tuve un inconveniente momentáneo. "
                "Por favor intenta de nuevo en unos segundos.\n\n"
                "Escribe *inicio* para reiniciar."
            )

        if not reply or not reply.strip():
            reply = (
                "Estoy aquí para ayudarte. Escribe *menu*, *pedido* o *reservar*."
            )

        response.message(reply)
        return str(response), 200, {"Content-Type": "application/xml"}

    @flask_app.post("/bot/reload-flow")
    def reload_flow():
        flow_engine.reload_flow()
        return {"status": "flow reloaded"}

    return flask_app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
