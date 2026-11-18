from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from orbit_launcher.app import seed
from orbit_launcher.models import Entry
from orbit_launcher.ui import EntryDialog, LauncherWindow


def test_search_keyboard_and_launch_only_selected(app, store, monkeypatch):
    seed(store, True)
    opened = []
    monkeypatch.setattr("orbit_launcher.ui.launch", lambda e: opened.append(e.name))
    window = LauncherWindow(store, desktop=False)
    window.show()
    app.processEvents()
    window.search_box.setText("GitHub")
    assert window.results.count() == 1
    QTest.keyClick(window.search_box, Qt.Key.Key_Return)
    assert opened == ["GitHub"]
    assert next(e for e in store.entries() if e.name == "GitHub").launches == 1
    window.close()


def test_calculator_copy_and_empty_state(app, store):
    window = LauncherWindow(store, desktop=False)
    window.show()
    window.search_box.setText("12 * 8")
    window.activate_selected()
    assert app.clipboard().text() == "96"
    window.search_box.setText("no match")
    assert window.empty.isVisible()
    window.close()


def test_dialog_validation_and_save(app):
    dialog = EntryDialog()
    dialog.name.setText("Example")
    dialog.kind.setCurrentIndex(dialog.kind.findData("url"))
    dialog.target.setText("javascript:alert(1)")
    dialog.validate()
    assert dialog.result_entry is None
    dialog.target.setText("https://example.com")
    dialog.validate()
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_entry.target == "https://example.com"


def test_navigation_and_pin(app, store):
    store.save(Entry.create("Docs", "https://docs.python.org", "url"))
    window = LauncherWindow(store, desktop=False)
    window.pin(store.entries()[0])
    window.set_mode("favorites")
    assert window.results.count() == 1
    window.set_mode("app")
    assert window.results.count() == 0
    window.close()
