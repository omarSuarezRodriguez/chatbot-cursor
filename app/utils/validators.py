import re
from datetime import date, datetime, time
from typing import Optional, Tuple


def normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def is_global_command(text: str) -> bool:
    return normalize_text(text) in {
        "menu",
        "pedido",
        "reservar",
        "inicio",
        "cancelar",
    }


def parse_persons(text: str) -> Optional[int]:
    cleaned = normalize_text(text)
    match = re.search(r"(\d+)", cleaned)
    if match:
        value = int(match.group(1))
        if 1 <= value <= 30:
            return value

    words = {
        "una": 1,
        "uno": 1,
        "un": 1,
        "dos": 2,
        "tres": 3,
        "cuatro": 4,
        "cinco": 5,
        "seis": 6,
        "siete": 7,
        "ocho": 8,
        "nueve": 9,
        "diez": 10,
    }
    for word, qty in words.items():
        if word in cleaned.split():
            return qty
    return None


def parse_date(text: str) -> Optional[date]:
    cleaned = normalize_text(text)
    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
            if parsed >= date.today():
                return parsed
        except ValueError:
            continue

    match = re.search(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", cleaned)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        year = match.group(3)
        if year:
            year_int = int(year)
            if year_int < 100:
                year_int += 2000
        else:
            year_int = date.today().year
        try:
            parsed = date(year_int, month, day)
            if parsed >= date.today():
                return parsed
        except ValueError:
            return None
    return None


def parse_time(text: str) -> Optional[time]:
    cleaned = normalize_text(text).replace("hrs", "").replace("hr", "").strip()
    formats = ["%H:%M", "%H.%M", "%I:%M %p", "%I:%M%p"]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).time()
        except ValueError:
            continue

    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", cleaned)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)

    if meridiem == "pm" and hour < 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0

    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return time(hour, minute)
    return None


def is_confirmation(text: str) -> bool:
    return normalize_text(text) in {
        "si",
        "sí",
        "confirmo",
        "confirmar",
        "ok",
        "dale",
        "correcto",
        "yes",
    }


def is_rejection(text: str) -> bool:
    return normalize_text(text) in {
        "no",
        "nop",
        "cancelar",
        "cambiar",
        "modificar",
    }


def validate_reservation_slot(
    reservation_date: date,
    reservation_time: time,
) -> Tuple[bool, str]:
    if reservation_date == date.today():
        now = datetime.now().time()
        if reservation_time <= now:
            return False, "La hora debe ser posterior a la hora actual."
    return True, ""
