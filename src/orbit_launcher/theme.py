"""Two coordinated palettes; all icons are drawn locally."""

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontDatabase, QIcon, QPainter, QPen, QPixmap


def load_fonts():
    """The offscreen Qt plugin does not enumerate Windows system fonts itself."""
    fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for filename in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "seguisym.ttf"):
        path = fonts / filename
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))


PALETTES = {
    "dark": {
        "bg": "#0c1020",
        "panel": "#13192d",
        "surface": "#1b2340",
        "border": "#2a3454",
        "text": "#eef1fc",
        "muted": "#a0acc8",
        "accent": "#b9a1ff",
    },
    "light": {
        "bg": "#f5f5fc",
        "panel": "#ffffff",
        "surface": "#eceafb",
        "border": "#dcdff0",
        "text": "#20243c",
        "muted": "#64708b",
        "accent": "#6540d7",
    },
}


def icon() -> QIcon:
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#8e6bef"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 120, 120, 32, 32)
    painter.setPen(QPen(QColor("#ffffff"), 7))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(27, 34, 74, 60)
    painter.drawEllipse(41, 21, 46, 86)
    painter.setBrush(QColor("#ffffff"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(88, 37, 14, 14)
    painter.end()
    return QIcon(pixmap)


def stylesheet(theme: str) -> str:
    p = PALETTES.get(theme, PALETTES["dark"])
    return f"""
    QWidget {{ background: {p["bg"]}; color: {p["text"]}; font-family: 'Segoe UI', 'Segoe UI Symbol'; font-size: 13px; }}
    QWidget#sidebar, QWidget#sidebar QLabel {{ background: {p["panel"]}; }}
    QWidget#sidebar {{ border-right: 1px solid {p["border"]}; }}
    QLabel#brand {{ font-size: 25px; font-weight: 750; letter-spacing: 2px; }}
    QLabel#heading {{ font-size: 27px; font-weight: 700; }}
    QLabel#muted {{ color: {p["muted"]}; }}
    QLabel#eyebrow {{ color: {p["accent"]}; font-size: 11px; font-weight: 650; letter-spacing: 2px; }}
    QLabel#badge {{ background: {p["surface"]}; color: {p["accent"]}; border-radius: 11px; padding: 5px 10px; }}
    QLabel#glyph {{ background: {p["surface"]}; color: {p["accent"]}; border-radius: 12px; font-size: 20px; font-weight: 700; }}
    QLabel#status {{ color: {p["muted"]}; padding: 8px 0; }}
    QPushButton {{ background: {p["surface"]}; border: 1px solid {p["border"]}; border-radius: 9px; padding: 9px 13px; }}
    QPushButton:hover {{ border-color: {p["accent"]}; }}
    QPushButton:pressed {{ background: {p["border"]}; }}
    QPushButton:disabled {{ color: {p["muted"]}; }}
    QPushButton#primary {{ background: #8e6bef; color: white; border: none; font-weight: 600; }}
    QPushButton#primary:hover {{ background: #9c7cf3; }}
    QPushButton#nav {{ text-align: left; background: transparent; border: none; padding: 12px; color: {p["muted"]}; }}
    QPushButton#nav:checked {{ background: {p["surface"]}; color: {p["text"]}; }}
    QPushButton#small {{ padding: 5px 9px; border: none; background: transparent; }}
    QLineEdit, QComboBox {{ background: {p["panel"]}; border: 1px solid {p["border"]}; border-radius: 9px; padding: 11px; selection-background-color: #7957d5; }}
    QLineEdit:focus, QComboBox:focus {{ border-color: {p["accent"]}; }}
    QLineEdit#search {{ font-size: 17px; padding: 16px; border-radius: 12px; }}
    QListWidget {{ border: none; background: transparent; outline: none; }}
    QListWidget::item {{ border: 1px solid transparent; border-radius: 12px; margin: 3px 0; }}
    QListWidget::item:selected {{ background: {p["surface"]}; border-color: {p["border"]}; }}
    QListWidget::item:hover {{ border-color: {p["border"]}; }}
    QWidget#row, QWidget#row QLabel {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 6px; }}
    QScrollBar::handle:vertical {{ background: {p["border"]}; border-radius: 3px; min-height: 30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QMenu {{ background: {p["panel"]}; border: 1px solid {p["border"]}; padding: 6px; }}
    QMenu::item {{ padding: 8px 20px; }}
    QMenu::item:selected {{ background: {p["surface"]}; }}
    QCheckBox {{ spacing: 8px; }}
    QToolTip {{ background: {p["panel"]}; color: {p["text"]}; border: 1px solid {p["border"]}; padding: 6px; }}
    """
