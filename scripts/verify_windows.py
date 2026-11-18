"""Exercise Windows hotkey registration and bundled EXE without opening user files."""

import ctypes
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from orbit_launcher.platforms import HOTKEYS

root = Path(__file__).resolve().parents[1]
report = {"platform": sys.platform}
if sys.platform == "win32":
    mods, key = HOTKEYS["Ctrl+Alt+Space"]
    registered = bool(ctypes.windll.user32.RegisterHotKey(None, 0x4F54, mods, key))
    report["hotkey_registered"] = registered
    if registered:
        report["hotkey_unregistered"] = bool(ctypes.windll.user32.UnregisterHotKey(None, 0x4F54))
    else:
        report["hotkey_note"] = "Combination already occupied; UI exposes alternatives."
env = os.environ.copy()
env["QT_QPA_PLATFORM"] = "offscreen"
binary = root / "dist" / "OrbitLauncher" / "OrbitLauncher.exe"
result = subprocess.run(
    [str(binary), "--smoke", "--demo", "--data-dir", str(root / ".qa" / "exe-smoke")],
    env=env,
    timeout=30,
    capture_output=True,
)
report["exe_exit_code"] = result.returncode
report["exe_created_database"] = (root / ".qa" / "exe-smoke" / "orbit.sqlite3").exists()
assert result.returncode == 0, result.stderr.decode(errors="replace")
assert report["exe_created_database"]
(root / ".qa").mkdir(exist_ok=True)
(root / ".qa" / "windows-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
