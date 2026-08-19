"""Peer-instance heartbeat for coordinating multi-instance access to shared state.

When multiple SkillManager instances are running, each writes a small
heartbeat file (``peer_heartbeat.json``) into the data directory.
New instances check this file before running expensive discovery — if
a peer wrote within the last *stale_seconds* (default 60s), the new
instance skips initial discovery and loads from the existing cache.

The heartbeat file is tiny (PID + timestamp) and written atomically.
If it's stale (peer crashed or was killed), the new instance proceeds
with a full discovery as usual.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

HEARTBEAT_FILENAME = "peer_heartbeat.json"
DEFAULT_STALE_SECONDS = 60.0


class PeerHeartbeat:
    """Read/write a peer-instance heartbeat file in the data directory."""

    def __init__(
        self, data_dir: str | Path, *, stale_seconds: float = DEFAULT_STALE_SECONDS
    ) -> None:
        self._path = Path(data_dir) / HEARTBEAT_FILENAME
        self._stale_seconds = stale_seconds

    def write(self) -> None:
        """Write a heartbeat with the current PID and timestamp."""
        try:
            payload = {"pid": os.getpid(), "ts": time.time()}
            self._path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            logger.debug("Failed to write peer heartbeat to %s", self._path, exc_info=True)

    def read(self) -> dict | None:
        """Read the heartbeat file. Returns None if missing or corrupt."""
        if not self._path.exists():
            return None
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def is_recent(self) -> bool:
        """Return True if a peer wrote a heartbeat within *stale_seconds*.

        A heartbeat is considered recent if:
        - The file exists and is valid JSON.
        - The timestamp is within the stale window.
        - The PID is *not* our own (avoids false-positive on restart).
        """
        data = self.read()
        if data is None:
            return False
        try:
            ts = float(data.get("ts", 0))
            pid = int(data.get("pid", 0))
        except (TypeError, ValueError):
            return False
        if pid == os.getpid():
            return False  # our own heartbeat from a previous run — not a peer
        age = time.time() - ts
        return age < self._stale_seconds

    def remove(self) -> None:
        """Delete the heartbeat file (called on graceful shutdown)."""
        try:
            if self._path.exists():
                self._path.unlink()
        except OSError:
            pass
