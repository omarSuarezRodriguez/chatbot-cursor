"""Quick local parity check for production-like env setup.

Usage:
    python scripts/check_unified_env.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _ok(name: str, value: bool, detail: str = "") -> str:
    icon = "OK" if value else "MISS"
    suffix = f" ({detail})" if detail else ""
    return f"[{icon}] {name}{suffix}"


def main() -> int:
    _load_env_file(ROOT / ".env.unified")
    _load_env_file(ROOT / ".env")
    _load_env_file(ROOT / ".env.dashboard")

    required = [
        "GOOGLE_SPREADSHEET_ID",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_WHATSAPP_FROM",
        "ADMIN_WHATSAPP_NUMBER",
        "BOT_HEALTH_URL",
        "DASHBOARD_ENABLE_WRITES",
    ]

    lines: list[str] = []
    missing = 0
    for key in required:
        val = os.environ.get(key, "").strip()
        is_set = bool(val)
        if key == "DASHBOARD_ENABLE_WRITES":
            is_set = val in {"0", "1"}
        if not is_set:
            missing += 1
        lines.append(_ok(key, is_set))

    json_blob = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    cred_path = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_PATH", "").strip()
    has_json = bool(json_blob)
    has_file = bool(cred_path) and Path(cred_path).is_file()
    creds_ok = has_json or has_file
    if not creds_ok:
        missing += 1
    lines.append(_ok("Google credentials", creds_ok, "JSON or credentials file"))

    if has_json:
        try:
            parsed = json.loads(json_blob)
            lines.append(_ok("GOOGLE_SERVICE_ACCOUNT_JSON format", isinstance(parsed, dict)))
        except json.JSONDecodeError:
            missing += 1
            lines.append(_ok("GOOGLE_SERVICE_ACCOUNT_JSON format", False))

    print("\n".join(lines))
    if missing:
        print(f"\nResult: {missing} checks missing. Fix before git push.")
        return 1
    print("\nResult: all required production-parity checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
