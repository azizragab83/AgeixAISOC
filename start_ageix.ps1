# ═══════════════════════════════════════════════════════
# AgeixAISOC - One-Click Startup Script
# Starts Backend (8000) + Frontend (5173) in separate windows
# ═══════════════════════════════════════════════════════

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗"
Write-Host "  ║        🚀 AgeixAISOC Launch Sequence        ║"
Write-Host "  ╚══════════════════════════════════════════════╝"
Write-Host ""

# 1. Activate the Python virtual environment
Write-Host "[1/3] Activating Python virtual environment..." -ForegroundColor Cyan
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "      ✓ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Warning "      ⚠ venv not found at .\venv\Scripts\Activate.ps1 - continuing without activation"
}

# Resolve the project root directory (this script's location)
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"

# 2. Open a new PowerShell window for the Backend
Write-Host "[2/3] Starting Backend on port 8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Write-Host 'AgeixAISOC Backend starting...' -ForegroundColor Green; " +
    "Set-Location '$backendDir'; " +
    "uvicorn main:app --reload --host 0.0.0.0 --port 8000"
)
Write-Host "      ✓ Backend window launched" -ForegroundColor Green

Start-Sleep -Seconds 2

# 3. Open a new PowerShell window for the Frontend
Write-Host "[3/3] Starting Frontend on port 5173..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Write-Host 'AgeixAISOC Frontend starting...' -ForegroundColor Green; " +
    "Set-Location '$frontendDir'; " +
    "npm run dev"
)
Write-Host "      ✓ Frontend window launched" -ForegroundColor Green

Start-Sleep -Seconds 2

# 4. Success message
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════════╗"
Write-Host "  ║  🚀 AgeixAISOC Platform is RUNNING!                    ║"
Write-Host "  ║                                                       ║"
Write-Host "  ║  Dashboard: http://localhost:5173                    ║"
Write-Host "  ║  Backend:   http://localhost:8000                    ║"
Write-Host "  ║  API Docs:  http://localhost:8000/docs               ║"
Write-Host "  ║  WS:        ws://localhost:8000/ws/dashboard         ║"
Write-Host "  ╚══════════════════════════════════════════════════════╝"
Write-Host ""
Write-Host "Press any key to close this window (services keep running)..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")