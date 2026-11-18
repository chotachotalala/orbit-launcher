# Third-party components

The application uses unmodified PySide6 and Qt shared libraries, installed from PyPI.
The portable distribution includes license texts from the installed PySide6,
PySide6_Essentials and shiboken6 distributions in `licenses/`.

- PySide6 / Qt for Python: https://pypi.org/project/PySide6/
- Qt for Python sources: https://code.qt.io/cgit/pyside/pyside-setup.git/
- Qt sources: https://code.qt.io/cgit/qt/qtbase.git/
- Qt licensing information: https://doc.qt.io/qt-6/licensing.html
- Python: https://www.python.org/psf/license/
- PyInstaller bootloader: https://pyinstaller.org/en/stable/license.html

The executable is built in directory mode. Qt DLLs remain separate in `_internal`
and can be replaced by compatible builds. The application's Python sources are
provided in the companion source ZIP under the MIT license.

No third-party images, icon packs or downloaded fonts are embedded. The logo is
drawn by application code, and fonts are loaded from the user's Windows installation.
