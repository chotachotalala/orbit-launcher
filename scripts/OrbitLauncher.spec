# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis([str(root / 'scripts' / 'entry.py')], pathex=[str(root / 'src')],
             binaries=[], datas=[], hiddenimports=[], hookspath=[], hooksconfig={},
             runtime_hooks=[], excludes=[], noarchive=False, optimize=0)
# Qt uses the Windows ICU API. A developer's PATH can contain another icuuc.dll
# with version-suffixed exports; bundling that DLL breaks an otherwise valid EXE.
a.binaries = [item for item in a.binaries
              if Path(item[0]).name.lower() not in {'icuuc.dll', 'icuin.dll', 'icudt78.dll'}]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='OrbitLauncher',
          debug=False, strip=False, upx=False, console=False,
          icon=str(root / 'docs' / 'assets' / 'orbit.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='OrbitLauncher')
