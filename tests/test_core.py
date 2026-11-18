import json
import sqlite3
from dataclasses import replace

import pytest

from orbit_launcher.models import Entry
from orbit_launcher.search import calculate, search
from orbit_launcher.storage import Store


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///C:/secret",
        "https://",
        "https://user:pass@example.com",
        "https://example.com:bad",
    ],
)
def test_rejects_non_web_or_credential_urls(url):
    with pytest.raises(ValueError):
        Entry.create("Test", url, "url")


def test_search_supports_aliases_layout_typos_and_favorites():
    entries = [
        Entry.create("GitHub", "https://github.com", "url", favorite=True),
        Entry.create("Блокнот", "notepad.exe", aliases="заметки текст"),
        Entry.create("GitLab", "https://gitlab.com", "url"),
    ]
    assert search(entries, "пшерги")[0].name == "GitHub"
    assert search(entries, "заметки")[0].name == "Блокнот"
    assert search(entries, "GitHbu")[0].name == "GitHub"
    assert [e.name for e in search(entries, "Git", "favorites")] == ["GitHub"]
    assert search(entries, "нет такого приложения") == []


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 3 * 4", "14"),
        ("=(1250 * 0,8) / 2", "500"),
        ("-5 + 2", "-3"),
        ("2 ** 8", "256"),
        ("10 // 3", "3"),
        ("1/0", None),
        ("__import__('os').system('calc')", None),
        ("2**1000000000", None),
        ("10**12**12", None),
        ("[1]*100000000", None),
        ("(1).__class__", None),
        ("(-1)**0.5", None),
        ("1e309 + 1", None),
        ("2 + True", None),
    ],
)
def test_safe_calculator(expression, expected):
    assert calculate(expression) == expected


def test_persists_updates_and_usage(tmp_path):
    path = tmp_path / "data.sqlite3"
    entry = Entry.create("Example", "https://example.com", "url")
    db = Store(path)
    db.save(entry)
    db.used(entry.id)
    db.save(replace(entry, name="Renamed", favorite=True))
    db.close()
    db = Store(path)
    saved = db.entries()[0]
    assert (saved.name, saved.favorite, saved.launches) == ("Renamed", True, 1)
    assert saved.last_used > 0
    db.close()


def test_duplicate_targets_rejected(store):
    store.save(Entry.create("One", "https://example.com", "url"))
    with pytest.raises(sqlite3.IntegrityError):
        store.save(Entry.create("Two", "https://example.com", "url"))


def test_import_roundtrip_merges_without_duplicates(store, tmp_path):
    entry = Entry.create("Example", "https://example.com", "url", favorite=True)
    store.save(entry)
    path = tmp_path / "backup.json"
    store.export_to(path)
    assert store.import_from(path) == 0
    other = Store(tmp_path / "other.db")
    assert other.import_from(path) == 1
    assert other.entries()[0].favorite
    other.close()


def test_invalid_import_is_atomic(store, tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "format": "orbit-launcher",
                "version": 1,
                "entries": [
                    Entry.create("OK", "https://example.com", "url").to_dict(),
                    {"name": "Broken"},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        store.import_from(path)
    assert store.entries() == []


def test_customized_indexed_shortcut_survives_reindex(store):
    indexed = replace(Entry.create("App", "C:/app.lnk"), source="index")
    store.replace_index([indexed])
    store.save(replace(store.entries()[0], favorite=True))
    store.replace_index([])
    assert store.entries()[0].favorite
    assert store.entries()[0].source == "manual"


def test_recent_order_and_deletion(store):
    a, b = Entry.create("A", "a.exe"), Entry.create("B", "b.exe")
    store.save(a)
    store.save(b)
    store.used(b.id)
    assert [e.id for e in search(store.entries(), "", "recent")] == [b.id]
    store.delete(b.id)
    assert search(store.entries(), "", "recent") == []
