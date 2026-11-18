import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtWidgets import QApplication

from orbit_launcher.storage import Store
from orbit_launcher.theme import load_fonts


@pytest.fixture(scope="session")
def app():
    app = QApplication.instance() or QApplication([])
    load_fonts()
    app.setStyle("Fusion")
    yield app


@pytest.fixture
def store(tmp_path):
    instance = Store(tmp_path / "orbit.db")
    yield instance
    instance.close()
