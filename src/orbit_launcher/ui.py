"""Qt desktop interface. Storage and launch adapters remain independently testable."""

import sqlite3
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .models import KINDS, Entry
from .platforms import HOTKEYS, GlobalHotkey, discover_shortcuts, launch
from .search import calculate, search
from .storage import Store
from .theme import icon, stylesheet


def label(text: str, style: str = "", wrap=False) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(style)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    return widget


def button(text, callback, style=""):
    widget = QPushButton(text)
    widget.setObjectName(style)
    widget.clicked.connect(callback)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


class EntryDialog(QDialog):
    def __init__(self, parent=None, entry: Entry | None = None):
        super().__init__(parent)
        self.entry = entry
        self.result_entry = None
        self.setWindowTitle("Изменить запись" if entry else "Добавить в Orbit")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(label(self.windowTitle(), "heading"))
        form = QFormLayout()
        form.setSpacing(12)
        self.name = QLineEdit(entry.name if entry else "")
        self.name.setMaxLength(120)
        self.name.setPlaceholderText("Например, Рабочие проекты")
        self.kind = QComboBox()
        for key, title in KINDS.items():
            self.kind.addItem(title, key)
        self.target = QLineEdit(entry.target if entry else "")
        self.target.setPlaceholderText("Путь к объекту или https://example.com")
        self.aliases = QLineEdit(entry.aliases if entry else "")
        self.aliases.setMaxLength(500)
        self.aliases.setPlaceholderText("Дополнительные слова для поиска")
        self.favorite = QCheckBox("Закрепить в избранном")
        self.favorite.setChecked(entry.favorite if entry else False)
        if entry:
            self.kind.setCurrentIndex(self.kind.findData(entry.kind))
        target_row = QHBoxLayout()
        target_row.addWidget(self.target)
        target_row.addWidget(button("Обзор…", self.browse))
        form.addRow("Название", self.name)
        form.addRow("Тип", self.kind)
        form.addRow("Адрес", target_row)
        form.addRow("Ключевые слова", self.aliases)
        layout.addLayout(form)
        layout.addWidget(self.favorite)
        self.error = label("", "muted", True)
        layout.addWidget(self.error)
        actions = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        actions.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        actions.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        actions.accepted.connect(self.validate)
        actions.rejected.connect(self.reject)
        layout.addWidget(actions)

    def browse(self):
        if self.kind.currentData() == "folder":
            path = QFileDialog.getExistingDirectory(self, "Выберите папку")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Выберите файл или программу")
        if path:
            self.target.setText(path)
            if not self.name.text().strip():
                self.name.setText(Path(path).stem)

    def validate(self):
        try:
            value = Entry.create(
                self.name.text(),
                self.target.text(),
                self.kind.currentData(),
                aliases=self.aliases.text(),
                favorite=self.favorite.isChecked(),
            )
            if value.kind != "url" and not Path(value.target).exists():
                raise ValueError("По этому пути ничего не найдено. Выберите существующий объект.")
            if self.entry:
                value = replace(
                    self.entry,
                    name=value.name,
                    target=value.target,
                    kind=value.kind,
                    aliases=value.aliases,
                    favorite=value.favorite,
                )
            self.result_entry = value
            self.accept()
        except ValueError as error:
            self.error.setText(str(error))


class IndexWorker(QThread):
    ready = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            self.ready.emit(discover_shortcuts())
        except OSError as error:
            self.failed.emit(str(error))


class LauncherWindow(QWidget):
    def __init__(self, store: Store, *, desktop=True):
        super().__init__()
        self.store, self.desktop = store, desktop
        self.mode = "all"
        self.matches = []
        self.answer = None
        self.worker = None
        self.tray = None
        self.hotkey = GlobalHotkey(self.toggle)
        self.setWindowTitle("Orbit Launcher")
        self.setWindowIcon(icon())
        self.setMinimumSize(920, 640)
        self.resize(1040, 710)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QHBoxLayout()
        body.setSpacing(0)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(216)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(20, 28, 20, 20)
        nav.setSpacing(7)
        nav.addWidget(label("◉  ORBIT", "brand"))
        nav.addWidget(label("Меньше кликов. Больше дела.", "muted"))
        nav.addSpacing(30)
        nav.addWidget(label("ВАШЕ ПРОСТРАНСТВО", "eyebrow"))
        nav.addSpacing(9)
        self.nav_buttons = {}
        for key, title in [
            ("all", "◈   Всё"),
            ("favorites", "☆   Избранное"),
            ("recent", "◷   Недавнее"),
            ("app", "▦   Программы"),
            ("documents", "▱   Файлы и папки"),
            ("url", "↗   Сайты"),
        ]:
            item = button(title, lambda checked=False, k=key: self.set_mode(k), "nav")
            item.setCheckable(True)
            nav.addWidget(item)
            self.nav_buttons[key] = item
        nav.addStretch()
        nav.addWidget(label("ОДНО СОЧЕТАНИЕ", "eyebrow"))
        self.hotkey_label = label(store.setting("hotkey", "Ctrl+Alt+Space"), "badge")
        nav.addWidget(self.hotkey_label)
        nav.addWidget(label("Открыть Orbit из любого окна", "muted", True))
        nav.addSpacing(18)
        nav.addWidget(button("⚙   Настройки", self.settings, "nav"))
        body.addWidget(sidebar)
        content = QVBoxLayout()
        content.setContentsMargins(30, 28, 30, 16)
        content.setSpacing(14)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.addWidget(label("БЫСТРЫЙ ЗАПУСК", "eyebrow"))
        heading.addWidget(label("Что откроем?", "heading"))
        header.addLayout(heading)
        header.addStretch()
        header.addWidget(button("+  Добавить", self.add_entry, "primary"))
        content.addLayout(header)
        self.search_box = QLineEdit()
        self.search_box.setObjectName("search")
        self.search_box.setPlaceholderText("Поиск программ, папок и сайтов…")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self.refresh)
        self.search_box.installEventFilter(self)
        self.search_box.returnPressed.connect(self.activate_selected)
        content.addWidget(self.search_box)
        info = QHBoxLayout()
        self.counter = label("", "muted")
        info.addWidget(self.counter)
        info.addStretch()
        info.addWidget(label("↑ ↓  выбор     Enter  открыть", "muted"))
        content.addLayout(info)
        self.results = QListWidget()
        self.results.setSpacing(2)
        self.results.itemActivated.connect(lambda _: self.activate_selected())
        self.results.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results.customContextMenuRequested.connect(self.context_menu)
        content.addWidget(self.results, 1)
        self.empty = label(
            "Пока здесь пусто.\nДобавьте объект или найдите программы в меню «Пуск».", "muted", True
        )
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content.addWidget(self.empty)
        bottom = QHBoxLayout()
        self.index_button = button("Найти программы", self.index_programs)
        bottom.addWidget(self.index_button)
        bottom.addStretch()
        bottom.addWidget(button("Открыть  ↵", self.activate_selected, "primary"))
        content.addLayout(bottom)
        self.status = label("Всё хранится на этом компьютере. Никаких аккаунтов.", "status", True)
        content.addWidget(self.status)
        body.addLayout(content, 1)
        outer.addLayout(body)
        self.shortcuts = []
        for sequence, callback in [
            ("Escape", self.hide_or_minimize),
            ("Ctrl+N", self.add_entry),
            ("Ctrl+Q", self.quit),
            ("Ctrl+F", self.search_box.setFocus),
        ]:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        self.apply_theme()
        self.set_mode("all")
        if desktop:
            self.setup_desktop()

    def apply_theme(self):
        QApplication.instance().setStyleSheet(stylesheet(self.store.setting("theme", "dark")))

    def setup_desktop(self):
        app = QApplication.instance()
        app.installNativeEventFilter(self.hotkey)
        if not self.hotkey.register(self.store.setting("hotkey", "Ctrl+Alt+Space")):
            self.notify("Горячая клавиша занята. Выберите другую в настройках.")
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(icon(), self)
            self.tray.setToolTip("Orbit Launcher")
            menu = QMenu(self)
            for text, callback in [
                ("Открыть Orbit", self.reveal),
                ("Настройки", self.settings),
                ("Выход", self.quit),
            ]:
                action = QAction(text, self)
                action.triggered.connect(callback)
                menu.addAction(action)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(
                lambda reason: (
                    self.toggle() if reason == QSystemTrayIcon.ActivationReason.Trigger else None
                )
            )
            self.tray.show()

    def set_mode(self, mode):
        self.mode = mode
        for key, item in self.nav_buttons.items():
            item.setChecked(key == mode)
        self.refresh()

    def refresh(self):
        entries = self.store.entries()
        if self.mode == "documents":
            entries = [e for e in entries if e.kind in {"folder", "file"}]
        self.matches = search(entries, self.search_box.text(), self.mode)
        self.answer = calculate(self.search_box.text())
        self.results.clear()
        if self.answer is not None:
            self.add_row(
                "=", self.answer, "Калькулятор · Enter — скопировать результат", "РЕЗУЛЬТАТ"
            )
        for entry in self.matches[:100]:
            glyph = {"app": "▦", "folder": "▱", "file": "≡", "url": "↗"}[entry.kind]
            subtitle = entry.target
            if len(subtitle) > 74:
                subtitle = subtitle[:34] + "…" + subtitle[-36:]
            self.add_row(
                glyph, entry.name, subtitle, ("★  " if entry.favorite else "") + KINDS[entry.kind]
            )
        count = len(self.matches)
        self.counter.setText(
            f"Найдено: {count}" + (" · показаны первые 100" if count > 100 else "")
        )
        is_empty = self.results.count() == 0
        self.empty.setVisible(is_empty)
        if is_empty and self.search_box.text():
            self.empty.setText(
                "Ничего не найдено.\nПопробуйте другое название или добавьте новую запись."
            )
        else:
            self.empty.setText(
                "Пока здесь пусто.\nДобавьте объект или найдите программы в меню «Пуск»."
            )
        self.results.setVisible(not is_empty)
        if not is_empty:
            self.results.setCurrentRow(0)

    def add_row(self, glyph, name, subtitle, badge):
        row = QWidget()
        row.setObjectName("row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(13)
        tile = label(glyph, "glyph")
        tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile.setFixedSize(43, 43)
        layout.addWidget(tile)
        texts = QVBoxLayout()
        texts.setSpacing(4)
        name_label = label(name)
        font = name_label.font()
        font.setBold(True)
        name_label.setFont(font)
        texts.addWidget(name_label)
        texts.addWidget(label(subtitle, "muted"))
        layout.addLayout(texts, 1)
        layout.addWidget(label(badge, "muted"))
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 76))
        self.results.addItem(item)
        self.results.setItemWidget(item, row)

    def selected_entry(self):
        row = self.results.currentRow() - (1 if self.answer is not None else 0)
        return self.matches[row] if 0 <= row < min(100, len(self.matches)) else None

    def activate_selected(self):
        if self.answer is not None and self.results.currentRow() == 0:
            QApplication.clipboard().setText(self.answer)
            self.notify("Результат скопирован.")
            return
        entry = self.selected_entry()
        if not entry:
            return
        try:
            launch(entry)
            self.store.used(entry.id)
            self.refresh()
            if self.store.setting("hide_after_launch", True):
                self.hide_or_minimize()
        except (OSError, ValueError) as error:
            self.notify(str(error))

    def add_entry(self):
        self.edit_entry(None)

    def edit_entry(self, entry):
        dialog = EntryDialog(self, entry)
        while dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.store.save(dialog.result_entry)
                self.refresh()
                self.notify("Запись сохранена.")
                return
            except sqlite3.IntegrityError:
                dialog.error.setText("Этот объект уже добавлен.")

    def context_menu(self, point):
        item = self.results.itemAt(point)
        if not item:
            return
        self.results.setCurrentItem(item)
        entry = self.selected_entry()
        if not entry:
            return
        menu = QMenu(self)
        menu.addAction(
            "Убрать из избранного" if entry.favorite else "В избранное", lambda: self.pin(entry)
        )
        menu.addAction("Изменить", lambda: self.edit_entry(entry))
        menu.addAction("Скопировать адрес", lambda: QApplication.clipboard().setText(entry.target))
        menu.addSeparator()
        menu.addAction("Удалить из Orbit", lambda: self.delete_entry(entry))
        menu.exec(self.results.viewport().mapToGlobal(point))

    def pin(self, entry):
        # Explicitly customized indexed shortcuts become durable user entries.
        self.store.save(replace(entry, favorite=not entry.favorite))
        if entry.source == "index":
            with self.store.db:
                self.store.db.execute("UPDATE entries SET source='manual' WHERE id=?", (entry.id,))
        self.refresh()

    def delete_entry(self, entry):
        answer = QMessageBox.question(
            self,
            "Удалить запись?",
            f"Убрать «{entry.name}» из Orbit? Сам объект останется на месте.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.store.delete(entry.id)
            self.refresh()

    def index_programs(self):
        if self.worker and self.worker.isRunning():
            return
        self.index_button.setEnabled(False)
        self.notify("Поиск ярлыков в меню «Пуск»…")
        self.worker = IndexWorker(self)
        self.worker.ready.connect(self.index_ready)
        self.worker.failed.connect(self.notify)
        self.worker.finished.connect(lambda: self.index_button.setEnabled(True))
        self.worker.start()

    def index_ready(self, entries):
        self.store.replace_index(entries)
        self.refresh()
        self.notify(f"Найдено ярлыков: {len(entries)}. Ваши записи сохранены.")

    def settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройки Orbit")
        dialog.setMinimumWidth(480)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(label("Сделайте Orbit своим", "heading"))
        form = QFormLayout()
        theme = QComboBox()
        theme.addItem("Тёмная", "dark")
        theme.addItem("Светлая", "light")
        theme.setCurrentIndex(theme.findData(self.store.setting("theme", "dark")))
        hotkey = QComboBox()
        hotkey.addItems(list(HOTKEYS))
        hotkey.setCurrentText(self.store.setting("hotkey", "Ctrl+Alt+Space"))
        hide = QCheckBox("Сворачивать Orbit после запуска объекта")
        hide.setChecked(self.store.setting("hide_after_launch", True))
        form.addRow("Оформление", theme)
        form.addRow("Горячая клавиша", hotkey)
        layout.addLayout(form)
        layout.addWidget(hide)
        layout.addWidget(
            label(
                "Экспорт включает добавленные вручную записи и избранное.\n"
                "Импорт добавляет новые объекты, не удаляя существующие.",
                "muted",
                True,
            )
        )
        data_row = QHBoxLayout()
        data_row.addWidget(button("Экспорт JSON", self.export_entries))
        data_row.addWidget(button("Импорт JSON", self.import_entries))
        layout.addLayout(data_row)
        error = label("", "muted", True)
        layout.addWidget(error)

        def save():
            if self.desktop and not self.hotkey.register(hotkey.currentText()):
                error.setText("Это сочетание занято другой программой. Выберите другое.")
                return
            self.store.set_setting("theme", theme.currentData())
            self.store.set_setting("hotkey", hotkey.currentText())
            self.store.set_setting("hide_after_launch", hide.isChecked())
            self.hotkey_label.setText(hotkey.currentText())
            self.apply_theme()
            dialog.accept()

        layout.addWidget(button("Сохранить настройки", save, "primary"))
        dialog.exec()

    def export_entries(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт записей", "orbit-backup.json", "JSON (*.json)"
        )
        if path:
            try:
                self.store.export_to(Path(path))
                self.notify("Экспорт сохранён.")
            except OSError as error:
                self.notify(str(error))

    def import_entries(self):
        path, _ = QFileDialog.getOpenFileName(self, "Импорт записей", "", "JSON (*.json)")
        if path:
            try:
                count = self.store.import_from(Path(path))
                self.refresh()
                self.notify(f"Добавлено записей: {count}. Ничего не запускалось.")
            except (OSError, ValueError, TypeError, sqlite3.Error) as error:
                self.notify(f"Не удалось импортировать: {error}")

    def notify(self, message):
        self.status.setText(message)

    def reveal(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.search_box.setFocus()
        self.search_box.selectAll()

    def toggle(self):
        if self.isVisible() and not self.isMinimized() and self.isActiveWindow():
            self.hide_or_minimize()
        else:
            self.reveal()

    def hide_or_minimize(self):
        self.hide() if self.tray and self.tray.isVisible() else self.showMinimized()

    def quit(self):
        self.hotkey.unregister()
        if self.worker and self.worker.isRunning():
            self.worker.wait()
        if self.tray:
            self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        if self.tray and self.tray.isVisible():
            self.hide()
            event.ignore()
        else:
            self.hotkey.unregister()
            if self.worker and self.worker.isRunning():
                self.worker.wait()
            event.accept()

    def eventFilter(self, obj, event):
        if obj is self.search_box and event.type() == QEvent.Type.KeyPress:
            if event.key() in {Qt.Key.Key_Down, Qt.Key.Key_Up}:
                delta = 1 if event.key() == Qt.Key.Key_Down else -1
                row = max(0, min(self.results.count() - 1, self.results.currentRow() + delta))
                self.results.setCurrentRow(row)
                return True
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.search_box.setFocus)
