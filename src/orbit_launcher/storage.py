"""SQLite persistence. Imports validate completely before changing the database."""

import json
import sqlite3
import time
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from .models import Entry


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, target TEXT NOT NULL,
                kind TEXT NOT NULL, aliases TEXT NOT NULL DEFAULT '',
                favorite INTEGER NOT NULL DEFAULT 0, launches INTEGER NOT NULL DEFAULT 0,
                last_used REAL NOT NULL DEFAULT 0, source TEXT NOT NULL DEFAULT 'manual',
                UNIQUE(kind, target)
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)

    def entries(self) -> list[Entry]:
        return [
            Entry(**{**dict(row), "favorite": bool(row["favorite"])})
            for row in self.db.execute("SELECT * FROM entries")
        ]

    def save(self, entry: Entry) -> None:
        with self.db:
            self.db.execute(
                """INSERT INTO entries VALUES
                (:id,:name,:target,:kind,:aliases,:favorite,:launches,:last_used,:source)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name,target=excluded.target,
                kind=excluded.kind,aliases=excluded.aliases,favorite=excluded.favorite,source='manual'
            """,
                entry.to_dict(),
            )

    def delete(self, entry_id: str) -> None:
        with self.db:
            self.db.execute("DELETE FROM entries WHERE id=?", (entry_id,))

    def used(self, entry_id: str) -> None:
        with self.db:
            self.db.execute(
                "UPDATE entries SET launches=launches+1,last_used=? WHERE id=?",
                (time.time(), entry_id),
            )

    def setting(self, key: str, default=None):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_setting(self, key: str, value) -> None:
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value))
            )

    def export_to(self, path: Path) -> None:
        payload = {
            "format": "orbit-launcher",
            "version": 1,
            "entries": [e.to_dict() for e in self.entries() if e.source != "index"],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def import_from(self, path: Path) -> int:
        if path.stat().st_size > 5_000_000:
            raise ValueError("Файл импорта слишком большой (максимум 5 МБ).")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(payload, dict)
            or payload.get("format") != "orbit-launcher"
            or payload.get("version") != 1
            or not isinstance(payload.get("entries"), list)
        ):
            raise ValueError("Это не файл экспорта Orbit Launcher версии 1.")
        if len(payload["entries"]) > 10_000:
            raise ValueError("В одном импорте допускается до 10 000 записей.")
        incoming = [replace(Entry.from_dict(row), source="manual") for row in payload["entries"]]
        count = 0
        with self.db:
            for entry in incoming:
                values = replace(entry, id=uuid4().hex).to_dict()
                cursor = self.db.execute(
                    """INSERT OR IGNORE INTO entries VALUES
                    (:id,:name,:target,:kind,:aliases,:favorite,:launches,:last_used,:source)
                """,
                    values,
                )
                count += cursor.rowcount
        return count

    def replace_index(self, entries: list[Entry]) -> None:
        with self.db:
            self.db.execute("DELETE FROM entries WHERE source='index'")
            for e in entries:
                self.db.execute(
                    """INSERT OR IGNORE INTO entries VALUES
                    (:id,:name,:target,:kind,:aliases,:favorite,:launches,:last_used,:source)
                """,
                    e.to_dict(),
                )

    def close(self):
        self.db.close()
