$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm scripts/OrbitLauncher.spec
if ($LASTEXITCODE -ne 0) { throw 'Сборка не завершена.' }
Write-Host 'Готово: dist\OrbitLauncher\OrbitLauncher.exe'
