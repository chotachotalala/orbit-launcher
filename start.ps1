$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (Test-Path -LiteralPath '.venv\Scripts\pythonw.exe') {
    Start-Process -FilePath '.venv\Scripts\pythonw.exe' -ArgumentList '-m orbit_launcher' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
} elseif (Test-Path -LiteralPath 'dist\OrbitLauncher\OrbitLauncher.exe') {
    Start-Process -FilePath 'dist\OrbitLauncher\OrbitLauncher.exe' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
} else {
    throw 'Сначала выполните setup.ps1 или распакуйте Windows-сборку в dist\OrbitLauncher.'
}
