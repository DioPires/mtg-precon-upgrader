"""SQLite response cache with TTL expiry."""

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any


def _cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME", "")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "commanderspellbook-mcp"


class Cache:
    """SQLite-backed cache with per-entry TTL."""

    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or (_cache_dir() / "combos.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cache ("
            "  key TEXT PRIMARY KEY,"
            "  value TEXT NOT NULL,"
            "  expires_at REAL NOT NULL"
            ")"
        )
        self._conn.commit()
        self._cleanup()

    def _cleanup(self) -> None:
        """Remove expired entries."""
        self._conn.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))
        self._conn.commit()

    @staticmethod
    def make_key(decklist: list[str]) -> str:
        """Create a cache key from a sorted decklist."""
        normalized = "\n".join(sorted(name.strip().lower() for name in decklist))
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        """Return cached value or None if missing/expired."""
        row = self._conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        value, expires_at = row
        if expires_at < time.time():
            self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn.commit()
            return None
        return json.loads(value)

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Store value with TTL in seconds."""
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), time.time() + ttl),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
