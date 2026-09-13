"""Live progress reporting for repair runs.

The orchestrator emits stage events through a reporter callback;
ProgressReporter persists them to a JSON file and can trigger a callback
(such as a dashboard re-render) after every event. Thread-safe: parallel
candidate verification emits events from worker threads.
"""

from __future__ import annotations

import datetime
import json
import os
import threading
from typing import Any, Callable, Optional


class ProgressReporter:
    def __init__(self, path: str, on_update: Optional[Callable[[], None]] = None) -> None:
        self.path = path
        self.on_update = on_update
        self._lock = threading.Lock()
        self._events: list[dict[str, Any]] = []

    def __call__(self, stage: str, **payload: Any) -> None:
        event = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "stage": stage,
            **payload,
        }
        with self._lock:
            self._events.append(event)
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"events": self._events}, fh, indent=2)
            os.replace(tmp, self.path)
        if self.on_update:
            self.on_update()

    @staticmethod
    def load(path: str) -> list[dict[str, Any]]:
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh).get("events", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []
