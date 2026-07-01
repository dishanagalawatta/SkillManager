"""Tests for the peer-instance heartbeat (peer_heartbeat.py)."""

import json
import os
import time
from pathlib import Path

from skill_manager.utils.peer_heartbeat import PeerHeartbeat


class TestPeerHeartbeat:
    """Tests for PeerHeartbeat read/write/is_recent."""

    def test_write_creates_file(self, tmp_path: Path):
        """write() creates a heartbeat JSON file."""
        hb = PeerHeartbeat(tmp_path)
        hb.write()

        hb_file = tmp_path / "peer_heartbeat.json"
        assert hb_file.exists()

        data = json.loads(hb_file.read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()
        assert "ts" in data

    def test_read_returns_data(self, tmp_path: Path):
        """read() returns the heartbeat data dict."""
        hb = PeerHeartbeat(tmp_path)
        hb.write()

        data = hb.read()
        assert data is not None
        assert data["pid"] == os.getpid()

    def test_read_missing_file(self, tmp_path: Path):
        """read() returns None when the file doesn't exist."""
        hb = PeerHeartbeat(tmp_path)
        assert hb.read() is None

    def test_read_corrupt_file(self, tmp_path: Path):
        """read() returns None when the file is corrupt."""
        hb = PeerHeartbeat(tmp_path)
        hb_file = tmp_path / "peer_heartbeat.json"
        hb_file.write_text("not json", encoding="utf-8")

        assert hb.read() is None

    def test_is_recent_own_pid(self, tmp_path: Path):
        """is_recent() returns False for our own PID (previous run)."""
        hb = PeerHeartbeat(tmp_path)
        hb.write()

        # Our own heartbeat should not be "recent" (it's from us, not a peer)
        assert hb.is_recent() is False

    def test_is_recent_stale(self, tmp_path: Path):
        """is_recent() returns False when the heartbeat is older than stale_seconds."""
        hb = PeerHeartbeat(tmp_path, stale_seconds=1.0)

        # Write a heartbeat with a fake PID and old timestamp
        hb_file = tmp_path / "peer_heartbeat.json"
        old_data = {"pid": 999999, "ts": time.time() - 10}
        hb_file.write_text(json.dumps(old_data), encoding="utf-8")

        assert hb.is_recent() is False

    def test_is_recent_peer(self, tmp_path: Path):
        """is_recent() returns True when a peer wrote recently."""
        hb = PeerHeartbeat(tmp_path, stale_seconds=60.0)

        # Write a heartbeat with a different PID and recent timestamp
        hb_file = tmp_path / "peer_heartbeat.json"
        peer_data = {"pid": 999999, "ts": time.time() - 5}
        hb_file.write_text(json.dumps(peer_data), encoding="utf-8")

        assert hb.is_recent() is True

    def test_remove(self, tmp_path: Path):
        """remove() deletes the heartbeat file."""
        hb = PeerHeartbeat(tmp_path)
        hb.write()
        assert (tmp_path / "peer_heartbeat.json").exists()

        hb.remove()
        assert not (tmp_path / "peer_heartbeat.json").exists()

    def test_remove_missing(self, tmp_path: Path):
        """remove() is a no-op when the file doesn't exist."""
        hb = PeerHeartbeat(tmp_path)
        hb.remove()  # Should not raise

    def test_write_oserror(self, tmp_path: Path, monkeypatch):
        """write() handles OSError gracefully."""
        hb = PeerHeartbeat(tmp_path)

        def boom(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(Path, "write_text", boom)
        hb.write()  # Should not raise
