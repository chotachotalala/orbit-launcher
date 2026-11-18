"""Create clean source and portable ZIPs, excluding local data and environments."""

import importlib.metadata
from pathlib import Path
from shutil import copy2, copytree
from zipfile import ZIP_DEFLATED, ZipFile

from release_files import source_files

root = Path(__file__).resolve().parents[1]
output = root / "releases"
output.mkdir(exist_ok=True)
binary = root / "dist" / "OrbitLauncher"
for distribution in ("PySide6", "PySide6_Essentials", "shiboken6"):
    dist = importlib.metadata.distribution(distribution)
    for file in dist.files or []:
        if "/licenses/" in str(file).replace("\\", "/"):
            source = Path(dist.locate_file(file))
            target = binary / "licenses" / distribution / Path(*file.parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            copy2(source, target)
for name in ("README.md", "LICENSE", "THIRD_PARTY.md"):
    copy2(root / name, binary / name)
copytree(root / "docs", binary / "docs", dirs_exist_ok=True)

source_zip = output / "orbit-launcher-1.0.0-source.zip"
with ZipFile(source_zip, "w", ZIP_DEFLATED) as archive:
    for path in source_files(root):
        archive.write(path, Path("orbit-launcher") / path.relative_to(root))
portable = output / "orbit-launcher-1.0.0-windows-x64.zip"
with ZipFile(portable, "w", ZIP_DEFLATED) as archive:
    for path in binary.rglob("*"):
        if path.is_file():
            archive.write(path, Path("OrbitLauncher") / path.relative_to(binary))
print(f"Source: {source_zip.name} ({source_zip.stat().st_size:,} bytes)")
print(f"Windows: {portable.name} ({portable.stat().st_size:,} bytes)")
