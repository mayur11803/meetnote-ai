import json
import os
from pathlib import Path
from datetime import datetime


class SessionManager:
    def __init__(self, storage_dir: str = "sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

    def save(self, session_id: str, data: dict):
        path = self.storage_dir / f"{session_id}.json"
        safe = {k: v for k, v in data.items()
                if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
        path.write_text(json.dumps(safe, default=str, indent=2))

    def load(self, session_id: str) -> dict:
        path = self.storage_dir / f"{session_id}.json"
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def list_sessions(self) -> list[dict]:
        sessions = []
        for f in sorted(self.storage_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text())
                sessions.append({
                    "session_id": f.stem,
                    "title": data.get("title", "Untitled"),
                    "status": data.get("status", "unknown"),
                    "started_at": data.get("started_at", ""),
                })
            except Exception:
                pass
        return sessions