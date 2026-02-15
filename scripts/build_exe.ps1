param(
    [switch]$Clean,
    [switch]$Smoke
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if ($Clean) {
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
    if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
}

python -m pip install --upgrade pyinstaller
python -m PyInstaller --noconfirm --onefile --name AIOS run_aios.py

if ($Smoke) {
    & ".\dist\AIOS.exe" --run "show policy"
    & ".\dist\AIOS.exe" --run "show dashboard"
}

Write-Host "Build complete: dist\\AIOS.exe"
