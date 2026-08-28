Write-Host 'Starting AgeixAISOC Platform...' -ForegroundColor Cyan
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& '.\venv\Scripts\Activate.ps1'
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'docker run -it --rm --name n8n-ageix -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n'
Start-Process powershell -ArgumentList '-NoExit', '-Command', '& ".\venv\Scripts\Activate.ps1"; uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 --app-dir .'
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'Set-Location .\frontend; npm run dev'
Write-Host 'Platform is RUNNING! Dashboard: http://localhost:5173' -ForegroundColor Green
