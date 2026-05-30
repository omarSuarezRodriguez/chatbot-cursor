"""Thread-safe per-user state with optional disk persistence."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_STATE = {
    "flow": "idle",
    "step": "start",
    "data": {},
}


class StateManager:
    def __init__(self, persist_path: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        self._states: Dict[str, Dict[str, Any]] = {}
        self._persist_path = Path(persist_path) if persist_path else None
        self._load()

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            with self._persist_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                self._states = payload
        except (json.JSONDecodeError, OSError):
            self._states = {}

    def _save(self) -> None:
        if not self._persist_path:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        with self._persist_path.open("w", encoding="utf-8") as handle:
            json.dump(self._states, handle, ensure_ascii=False, indent=2)

    def get(self, wa_id: str) -> Dict[str, Any]:
        with self._lock:
            if wa_id not in self._states:
                self._states[wa_id] = deepcopy(DEFAULT_STATE)
            return deepcopy(self._states[wa_id])

    def update(self, wa_id: str, **kwargs: Any) -> Dict[str, Any]:
        with self._lock:
            current = self.get(wa_id)
            current.update(kwargs)
            self._states[wa_id] = current
            self._save()
            return deepcopy(current)

    def set_step(self, wa_id: str, step: str, flow: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"step": step}
        if flow is not None:
            payload["flow"] = flow
        return self.update(wa_id, **payload)

    def set_data(self, wa_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.update(wa_id, data=data)

    def patch_data(self, wa_id: str, **fields: Any) -> Dict[str, Any]:
        state = self.get(wa_id)
        merged = {**state.get("data", {}), **fields}
        return self.update(wa_id, data=merged)

    def reset(self, wa_id: str) -> Dict[str, Any]:
        with self._lock:
            self._states[wa_id] = deepcopy(DEFAULT_STATE)
            self._save()
            return deepcopy(self._states[wa_id])

    def cancel(self, wa_id: str) -> Dict[str, Any]:
        return self.reset(wa_id)
