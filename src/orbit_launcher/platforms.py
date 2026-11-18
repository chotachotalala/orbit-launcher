"""Small Windows adapter: explicit launches, Start-menu discovery, global hotkey."""

import ctypes
import os
import sys
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QAbstractNativeEventFilter

from .models import Entry

HOTKEYS = {
    "Ctrl+Alt+Space": (0x0002 | 0x0001 | 0x4000, 0x20),
    "Alt+Space": (0x0001 | 0x4000, 0x20),
    "Ctrl+Shift+Space": (0x0002 | 0x0004 | 0x4000, 0x20),
}


def launch(entry: Entry) -> None:
    # Revalidate URLs read from disk too; never pass user text to a command shell.
    Entry.from_dict(entry.to_dict())
    if sys.platform != "win32":
        raise OSError("Запуск объектов поддерживается в Windows.")
    if entry.kind != "url" and not Path(entry.target).exists():
        raise FileNotFoundError("Объект перемещён или удалён. Исправьте путь в записи.")
    os.startfile(entry.target)


def discover_shortcuts() -> list[Entry]:
    roots = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
    ]
    entries, seen = [], set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.lnk"):
            key = str(path).casefold()
            if key in seen or any(w in path.stem.casefold() for w in ("uninstall", "удаление")):
                continue
            seen.add(key)
            entries.append(replace(Entry.create(path.stem, str(path)), source="index"))
    return entries


class GlobalHotkey(QAbstractNativeEventFilter):
    ID = 0x4F52

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.current = None

    def register(self, name: str) -> bool:
        if sys.platform != "win32" or name not in HOTKEYS:
            return False
        previous = self.current
        self.unregister()
        mods, key = HOTKEYS[name]
        if ctypes.windll.user32.RegisterHotKey(None, self.ID, mods, key):
            self.current = name
            return True
        if previous:
            mods, key = HOTKEYS[previous]
            if ctypes.windll.user32.RegisterHotKey(None, self.ID, mods, key):
                self.current = previous
        return False

    def unregister(self):
        if self.current and sys.platform == "win32":
            ctypes.windll.user32.UnregisterHotKey(None, self.ID)
        self.current = None

    def nativeEventFilter(self, event_type, message):
        if sys.platform == "win32":
            from ctypes.wintypes import MSG

            msg = MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == self.ID:
                self.callback()
                return True, 0
        return False, 0
