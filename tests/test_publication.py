"""Release archives must not silently collect local credentials or runtime data."""

import runpy
from pathlib import Path

import pytest

MANIFEST = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/release_files.py"))


@pytest.mark.parametrize(
    "private_path",
    [
        ".env",
        ".env.production",
        "docs/private.pem",
        "scripts/signing.key",
        "tests/secrets.pfx",
        "docs/id_ed25519",
        "docs/.session-key.backup",
        "docs/storage.sqlite3-wal",
        "docs/storage.db.backup",
        "data/notes.md",
        "backups/README.md",
        ".qa/output.py",
        "exports/orbit-backup.json",
    ],
)
def test_archive_rejects_private_files_at_any_depth(tmp_path, private_path):
    path = tmp_path / private_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("disposable private fixture", encoding="utf-8")
    assert list(MANIFEST["source_files"](tmp_path)) == []


def test_archive_keeps_source_build_spec_and_example_config(tmp_path):
    expected = {
        "README.md",
        ".gitignore",
        ".env.example",
        "src/demo/app.py",
        "scripts/OrbitLauncher.spec",
        "docs/assets/preview.png",
        ".github/workflows/checks.yml",
    }
    for name in expected:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("public fixture", encoding="utf-8")
    actual = {path.relative_to(tmp_path).as_posix() for path in MANIFEST["source_files"](tmp_path)}
    assert actual == expected


def test_unrecognized_root_files_are_not_published(tmp_path):
    (tmp_path / "personal-notes.txt").write_text("private fixture", encoding="utf-8")
    assert list(MANIFEST["source_files"](tmp_path)) == []
