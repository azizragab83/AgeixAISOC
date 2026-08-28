# ═══════════════════════════════════════════════════════
# AgeixAISOC - Stop Script
# Kills all related processes (Python, Node, npm, uvicorn, Vite)
# ═══════════════════════════════════════════════════════

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗"
Write-Host "  ║        🛑 AgeixAISOC Shutdown Sequence       ║"
Write-Host "  ╚══════════════════════════════════════════════╝"
Write-Host ""

$stopped = @()

# 1. Kill uvicorn / Python backend processes
Write-Host "[1/3] Stopping Backend (uvicorn/python)..." -ForegroundColor Cyan
$uvicorn = Get-Process -Name python, pythonw -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -match "uvicorn|main:app" -or $_.Id -in (Get-CimInstance Win32_Process -Filter "Name like 'python%'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "uvicorn" } | Select-Object -ExpandProperty ProcessId)
}
foreach ($p in $uvicorn) {
    try {
        Stop-Process -Id $p.Id -Force -ErrorAction Stop
        $stopped += "python (PID $($p.Id))"
        Write-Host "      ✓ Killed python (PID $($p.Id))" -ForegroundColor Green
    } catch {}
}

# Also kill any process with 'uvicorn' in the command line
$uvicornProcs = Get-CimInstance Win32_Process -Filter "Name like 'python%'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "uvicorn" }
foreach ($proc in $uvicornProcs) {
    try {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        $stopped += "uvicorn (PID $($proc.ProcessId))"
        Write-Host "      ✓ Killed uvicorn (PID $($proc.ProcessId))" -ForegroundColor Green
    } catch {}
}

# 2. Kill Node / Vite / npm frontend processes
Write-Host "[2/3] Stopping Frontend (node/vite/npm)..." -ForegroundColor Cyan
$nodeProcs = Get-CimInstance Win32_Process -Filter "Name like 'node%'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "vite|npm run dev|react" }
foreach ($proc in $nodeProcs) {
    try {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        $stopped += "node (PID $($proc.ProcessId))"
        Write-Host "      ✓ Killed node (PID $($proc.ProcessId))" -ForegroundColor Green
    } catch {}
}

# Kill any leftover cmd/powershell windows running vite or uvicorn
$cmdProcs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { 
    $_.CommandLine -match "npm run dev|vite|uvicorn main:app" -and $_.Name -match "cmd|powershell|conhost"
}
foreach ($proc in $cmdProcs) {
    try {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        $stopped += "$($proc.Name) (PID $($proc.ProcessId))"
        Write-Host "      ✓ Killed $($proc.Name) (PID $($proc.ProcessId))" -ForegroundColor Green
    } catch {}
}

# 3. Final cleanup check
Write-Host "[3/3] Final cleanup check..." -ForegroundColor Cyan
$remaining = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -match "vite|uvicorn main:app|npm run dev"
}
if ($remaining) {
    foreach ($proc in $remaining) {
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            $stopped += "$($proc.Name) (PID $($proc.ProcessId))"
            Write-Host "      ✓ Cleaned up $($proc.Name) (PID $($proc.ProcessId))" -ForegroundColor Green
        } catch {}
    }
}

Write-Host ""
if ($stopped.Count -gt 0) {
    Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "  ║   ✅ AgeixAISOC fully stopped!               ║" -ForegroundColor Green
    Write-Host "  ║   Terminated: $($stopped.Count) process(es)    ║" -ForegroundColor Green
    Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Green
} else {
    Write-Host "  No AgeixAISOC processes were found running." -ForegroundColor Yellow
}
Write-Host ""