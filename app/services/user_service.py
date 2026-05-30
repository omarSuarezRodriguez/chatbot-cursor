from __future__ import annotations

from app.integrations.google_sheets import GoogleSheetsClient


class UserService:
    def __init__(self, sheets: GoogleSheetsClient) -> None:
        self.sheets = sheets

    def touch(self, wa_id: str, name: str = "") -> None:
        self.sheets.upsert_user(wa_id=wa_id, name=name)
