"""Render the real Qt widgets with isolated demo data, without desktop capture."""

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication

from orbit_launcher.app import seed
from orbit_launcher.storage import Store
from orbit_launcher.theme import icon, load_fonts
from orbit_launcher.ui import EntryDialog, LauncherWindow

root = Path(__file__).resolve().parents[1]
assets = root / "docs" / "assets"
assets.mkdir(parents=True, exist_ok=True)
app = QApplication([])
load_fonts()
app.setStyle("Fusion")
with TemporaryDirectory(dir=root) as temp:
    store = Store(Path(temp) / "demo.db")
    seed(store, True)
    window = LauncherWindow(store, desktop=False)
    window.show()
    app.processEvents()
    window.grab().save(str(assets / "orbit-dark.png"))
    store.set_setting("theme", "light")
    window.apply_theme()
    app.processEvents()
    window.grab().save(str(assets / "orbit-light.png"))
    store.set_setting("theme", "dark")
    window.apply_theme()
    window.search_box.setText("(1250 * 0.8) / 2")
    app.processEvents()
    window.grab().save(str(assets / "orbit-calculator.png"))
    dialog = EntryDialog(window)
    dialog.show()
    app.processEvents()
    dialog.grab().save(str(assets / "orbit-add.png"))
    icon().pixmap(128, 128).save(str(assets / "orbit.ico"))
    dialog.close()
    window.close()
    store.close()
print("Rendered dark, light, calculator and add-dialog screenshots.")
