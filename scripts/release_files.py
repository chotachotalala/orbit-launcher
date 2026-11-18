"""Explicit source manifest shared by packaging and clean-copy tools.

An ignored file is not automatically safe to zip. Select known source locations
and file types, reject runtime/secret names at every depth, and never follow links.
"""

import os
import re
from pathlib import Path

ROOT_FILES = {
    ".gitignore",
    ".dockerignore",
    ".env.example",
    ".env.sample",
    ".env.template",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "THIRD_PARTY.md",
    "SECURITY.md",
    "PUBLICATION_AUDIT.md",
    "pyproject.toml",
    "requirements-lock.txt",
    "setup.ps1",
    "start.ps1",
    "Linklane.cmd",
    "Демонстрация.cmd",
    "Dockerfile",
    "compose.yaml",
}
SOURCE_DIRECTORIES = {"src", "tests", "scripts", "docs", ".github"}
SOURCE_SUFFIXES = {
    ".py",
    ".md",
    ".toml",
    ".txt",
    ".ps1",
    ".cmd",
    ".yml",
    ".yaml",
    ".css",
    ".js",
    ".html",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".ico",
    ".spec",
}
PRIVATE_DIRECTORIES = {
    ".venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".qa",
    "data",
    ".demo",
    "build",
    "dist",
    "releases",
    ".ssh",
    "logs",
    "backups",
    "exports",
}


def private_name(name: str) -> bool:
    value = name.casefold()
    return (
        value in {".env", ".netrc", ".pypirc"}
        or value.startswith(
            (".env.", ".session-key", "id_rsa", "id_ed25519", "orbit-backup", "linklane-export")
        )
        or bool(
            re.search(r"\.(?:sqlite3?|db|pem|key|p12|pfx|jks|keystore|kdbx|log)(?:\.|-|$)", value)
        )
    )


def linked(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def source_files(root: Path):
    root = root.resolve()
    for folder, directories, files in os.walk(root, followlinks=False):
        parent = Path(folder)
        at_root = parent == root
        directories[:] = sorted(
            name
            for name in directories
            if (not at_root or name in SOURCE_DIRECTORIES)
            and name not in PRIVATE_DIRECTORIES
            and not name.endswith(".egg-info")
            and not private_name(name)
            and not linked(parent / name)
        )
        for name in sorted(files):
            path = parent / name
            example = at_root and name in {".env.example", ".env.sample", ".env.template"}
            if linked(path) or (private_name(name) and not example):
                continue
            if at_root:
                allowed = name in ROOT_FILES
            else:
                allowed = path.suffix.casefold() in SOURCE_SUFFIXES
            if allowed:
                yield path
