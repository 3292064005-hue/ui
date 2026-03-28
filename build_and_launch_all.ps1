# Spine Ultrasound Platform - Windows Dev Launcher
Write-Host "[+] Initiating SPINE ULTRASOUND PLATFORM (Windows Development Build)..." -ForegroundColor Cyan

# 1. Build React/WebGL Frontend
Write-Host "[+] Building Modern Frontend..." -ForegroundColor Yellow
Set-Location -Path "ui_frontend"
npm install
npm run build
Set-Location -Path ".."

# 2. Skip C++ Core (Requires Linux RT)
Write-Host "[!] C++ 1ms Admittance Core skipped." -ForegroundColor Red
Write-Host "    (The ROKAE SDK and POSIX RT threads must be compiled on Ubuntu 22.04)" -ForegroundColor DarkGray

# 3. Setup Python Backend Environment
Write-Host "[+] Constructing GPU Python Sandbox..." -ForegroundColor Yellow
if (-Not (Test-Path -Path ".venv")) {
    python -m venv .venv
}
.venv\Scripts\Activate.ps1
pip install -r requirements-win-dev.txt

# 4. Triggering System Boot
Write-Host "[+] ==========================================" -ForegroundColor Green
Write-Host "[+] WINDOWS DEV SYSTEMS GO." -ForegroundColor Green
Write-Host "[+] Run '.venv\Scripts\Activate.ps1; python api_server_win_mock.py' to start the Headless API."
Write-Host "[+] To run the full robot C++ core, please deploy this folder to your Ubuntu 22.04 machine."
Write-Host "[+] ==========================================" -ForegroundColor Green
