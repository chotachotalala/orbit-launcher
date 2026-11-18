"""Application entry point, isolated demo mode and single-instance handoff."""

import argparse
import hashlib
import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from .models import Entry
from .storage import Store
from .theme import load_fonts
from .ui import LauncherWindow


def seed(store: Store, demo=False):
    if store.setting("initialized", False):
        return
    windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
    defaults = [
        Entry.create(
            "Калькулятор",
            str(windows / "System32/calc.exe"),
            aliases="calculator calc",
            favorite=True,
        ),
        Entry.create(
            "Блокнот",
            str(windows / "System32/notepad.exe"),
            aliases="notepad notes текст",
            favorite=True,
        ),
        Entry.create(
            "Python Docs",
            "https://docs.python.org/3/",
            "url",
            aliases="документация питон",
            favorite=True,
        ),
        Entry.create(
            "GitHub", "https://github.com", "url", aliases="код репозитории", favorite=True
        ),
    ]
    if demo:
        defaults.extend(
            [
                Entry.create("Дизайн проекта", "https://www.figma.com", "url", aliases="макет"),
                Entry.create("Рабочие проекты", r"C:\Projects", "folder", aliases="работа код"),
                Entry.create("Заметки к релизу", r"C:\Projects\release-notes.md", "file"),
            ]
        )
    for entry in defaults:
        store.save(entry)
    store.set_setting("initialized", True)


def main():
    parser = argparse.ArgumentParser(description="Orbit Launcher")
    parser.add_argument("--data-dir", type=Path, help="Override the local data directory")
    parser.add_argument("--demo", action="store_true", help="Use separate illustrative data")
    parser.add_argument(
        "--smoke", action="store_true", help="Open and close UI without desktop hooks"
    )
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    load_fonts()
    app.setApplicationName("Orbit Launcher")
    app.setStyle("Fusion")
    data = args.data_dir or Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / (
        "OrbitLauncher-Demo" if args.demo else "OrbitLauncher"
    )
    data = data.resolve()
    socket_name = "orbit-" + hashlib.sha256(str(data).casefold().encode()).hexdigest()[:20]
    socket = QLocalSocket()
    socket.connectToServer(socket_name)
    if socket.waitForConnected(200):
        socket.write(b"show")
        socket.waitForBytesWritten(500)
        return 0
    QLocalServer.removeServer(socket_name)
    server = QLocalServer()
    if not server.listen(socket_name):
        QMessageBox.critical(
            None, "Orbit Launcher", "Не удалось открыть локальный канал приложения."
        )
        return 1
    try:
        store = Store(data / "orbit.sqlite3")
        seed(store, args.demo)
    except Exception as error:
        QMessageBox.critical(None, "Orbit Launcher", f"Не удалось открыть хранилище: {error}")
        return 1
    window = LauncherWindow(store, desktop=not args.smoke)

    def connected():
        client = server.nextPendingConnection()
        if client:
            client.close()
            client.deleteLater()
        window.reveal()

    server.newConnection.connect(connected)
    app.aboutToQuit.connect(window.hotkey.unregister)
    window.show()
    if args.smoke:
        QTimer.singleShot(500, app.quit)
    result = app.exec()
    server.close()
    store.close()
    return result
