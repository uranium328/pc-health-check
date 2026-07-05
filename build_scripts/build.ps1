# 依序建置免安裝版（dist/PCHealthCheck.exe）與安裝版（dist/PCHealthCheckSetup.exe）。
# installer.spec 會把 PCHealthCheck.exe 內嵌進去，因此順序不能顛倒。
#
# 用法（在專案根目錄執行）：
#   powershell -File build_scripts\build.ps1
#
# 依據 docs/build-feasibility.md：本機 MS Store 版 Python 已驗證可直接建置，
# 這裡固定呼叫 `python`，若未來改用 python.org 建置 venv，只需改這一行。
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

python -m PyInstaller pyinstaller\app.spec --noconfirm
python -m PyInstaller installer\installer.spec --noconfirm

Write-Host "Build complete:"
Write-Host "  Portable : $ProjectRoot\dist\PCHealthCheck.exe"
Write-Host "  Installer: $ProjectRoot\dist\PCHealthCheckSetup.exe"
