"""Persistent local cache and an atomic rolling limit shared by local workers."""
import math
import sqlite3
import time
from contextlib import closing
from pathlib import Path


class RateLimitError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after


class DictionaryStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value BLOB NOT NULL, expires REAL NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS calls (at REAL NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def get(self, key: str) -> bytes | None:
        with closing(self.connect()) as db, db:
            db.execute("DELETE FROM cache WHERE expires <= ?", (time.time(),))
            row = db.execute("SELECT value FROM cache WHERE key = ?", (key,)).fetchone()
            return bytes(row[0]) if row else None

    def put(self, key: str, value: bytes, ttl: int):
        with closing(self.connect()) as db, db:
            db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?, ?)", (key, value, time.time() + ttl))

    def reserve_call(self, now: float | None = None):
        now = time.time() if now is None else now
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM calls WHERE at <= ?", (now - 60,))
            count, first = db.execute("SELECT COUNT(*), MIN(at) FROM calls").fetchone()
            if count >= 15:
                raise RateLimitError(max(1, math.ceil(first + 60 - now)))
            db.execute("INSERT INTO calls VALUES (?)", (now,))
