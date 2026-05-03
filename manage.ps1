# charging-self-report management script
param(
    [Parameter(Position=0)]
    [string]$Action = '',
    [Parameter(Position=1)]
    [switch]$Help
)

function Show-Help {
    Write-Host "Charging Self-Report Management Script" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\manage.ps1 <action>" -ForegroundColor White
    Write-Host ""
    Write-Host "Actions:" -ForegroundColor Yellow
    Write-Host "  start            Start both backend and frontend" -ForegroundColor White
    Write-Host "  stop             Stop both backend and frontend" -ForegroundColor White
    Write-Host "  restart          Restart both backend and frontend" -ForegroundColor White
    Write-Host "  status           Show service running status" -ForegroundColor White
    Write-Host "  backend-start    Start backend only (port 8100)" -ForegroundColor White
    Write-Host "  backend-stop     Stop backend only" -ForegroundColor White
    Write-Host "  frontend-start   Start frontend only (port 3000)" -ForegroundColor White
    Write-Host "  frontend-stop    Stop frontend only" -ForegroundColor White
    Write-Host "  help             Show this help message" -ForegroundColor White
}

if ($Help -or $Action -eq 'help' -or $Action -eq '-h' -or $Action -eq '--help' -or $Action -eq '') {
    Show-Help
    exit 0
}

$BackendPort = 8100
$FrontendPort = 3000
$BackendDir = "$PSScriptRoot\backend"
$FrontendDir = "$PSScriptRoot\frontend"

function Kill-Port {
    param([int]$Port)
    $conns = netstat -ano | Select-String ":$Port .*LISTENING"
    if ($conns) {
        $processIds = $conns | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -Unique
        foreach ($processId in $processIds) {
            Write-Host "  Killing PID $processId on port $Port" -ForegroundColor Yellow
            taskkill //F //PID $processId 2>$null
        }
        Start-Sleep -Seconds 1
    }
}

function Kill-Uvicorn {
    Write-Host "  Stopping uvicorn processes" -ForegroundColor Yellow
    Stop-Process -Name 'python', 'pythonw', 'uvicorn' -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    for ($i = 0; $i -lt 3; $i++) {
        $conns = netstat -ano | Select-String ":$BackendPort .*LISTENING"
        if (-not $conns) { break }
        $processIds = $conns | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -Unique
        foreach ($processId in $processIds) {
            Write-Host "  Killing PID $processId on port $BackendPort" -ForegroundColor Yellow
            taskkill //F //PID $processId 2>$null | Out-Null
        }
        Start-Sleep -Milliseconds 500
    }
}

function Kill-Vite {
    Write-Host "  Stopping vite processes" -ForegroundColor Yellow
    Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object {
        $_.CommandLine -match 'vite'
    } | ForEach-Object {
        Write-Host "  Killing vite node PID $($_.ProcessId)" -ForegroundColor Yellow
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Stop-Services {
    Write-Host "=== Stopping services ===" -ForegroundColor Cyan
    Kill-Uvicorn
    Kill-Vite
    Kill-Port -Port $FrontendPort
    Write-Host "All services stopped." -ForegroundColor Green
}

function Stop-Backend {
    Write-Host "=== Stopping backend ===" -ForegroundColor Cyan
    Kill-Uvicorn
    Write-Host "Backend stopped." -ForegroundColor Green
}

function Stop-Frontend {
    Write-Host "=== Stopping frontend ===" -ForegroundColor Cyan
    Kill-Vite
    Kill-Port -Port $FrontendPort
    Write-Host "Frontend stopped." -ForegroundColor Green
}

function Start-Backend {
    Write-Host "=== Starting backend (port $BackendPort) ===" -ForegroundColor Cyan
    $existing = netstat -ano | Select-String ":$BackendPort .*LISTENING"
    if ($existing) {
        Write-Host "  Backend already running on port $BackendPort" -ForegroundColor Yellow
        return $true
    }
    $job = Start-Process -FilePath 'python' -ArgumentList '-m', 'uvicorn', 'app.main:app', '--reload', '--host', '0.0.0.0', '--port', $BackendPort.ToString() -WindowStyle Hidden -PassThru -WorkingDirectory $BackendDir
    Write-Host "  Backend PID: $($job.Id)" -ForegroundColor Green
    Write-Host "  Waiting for backend..." -NoNewline
    for ($i = 0; $i -lt 40; $i++) {
        try {
            $r = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/health"
            if ($r.status -eq 'ok') { Write-Host " OK" -ForegroundColor Green; return $true }
        } catch {}
        Start-Sleep -Seconds 1
        Write-Host '.' -NoNewline
    }
    Write-Host " TIMEOUT" -ForegroundColor Red
    return $false
}

function Start-Frontend {
    Write-Host "=== Starting frontend (port $FrontendPort) ===" -ForegroundColor Cyan
    $cacheDir = Join-Path $FrontendDir 'node_modules\.vite'
    if (Test-Path $cacheDir) { Remove-Item -Recurse -Force $cacheDir }
    $existing = netstat -ano | Select-String ":$FrontendPort .*LISTENING"
    if ($existing) {
        Write-Host "  Frontend already running on port $FrontendPort" -ForegroundColor Yellow
        return $true
    }
    $job = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'npx.cmd', 'vite', '--port', $FrontendPort.ToString() -WindowStyle Hidden -PassThru -WorkingDirectory $FrontendDir
    Write-Host "  Frontend PID: $($job.Id)" -ForegroundColor Green
    Write-Host "  Waiting for frontend..." -NoNewline
    for ($i = 0; $i -lt 40; $i++) {
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:$FrontendPort" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            if ($r.StatusCode -eq 200) { Write-Host " OK" -ForegroundColor Green; return $true }
        } catch {}
        Start-Sleep -Seconds 1
        Write-Host '.' -NoNewline
    }
    Write-Host " TIMEOUT" -ForegroundColor Red
    return $false
}

function Start-Services {
    $ok1 = Start-Backend
    $ok2 = Start-Frontend
    if ($ok1 -and $ok2) {
        Write-Host "`n=== All services started ===" -ForegroundColor Green
        Write-Host "  Backend:  http://localhost:$BackendPort"
        Write-Host "  Frontend: http://localhost:$FrontendPort"
    } else {
        Write-Host "`n=== Some services failed to start ===" -ForegroundColor Red
    }
}

function Show-Status {
    Write-Host "=== Service Status ===" -ForegroundColor Cyan
    $bp = netstat -ano | Select-String ":$BackendPort .*LISTENING"
    $fp = netstat -ano | Select-String ":$FrontendPort .*LISTENING"
    if ($bp) { Write-Host "  Backend ($BackendPort):  Running" -ForegroundColor Green } else { Write-Host "  Backend ($BackendPort):  Stopped" -ForegroundColor Red }
    if ($fp) { Write-Host "  Frontend ($FrontendPort): Running" -ForegroundColor Green } else { Write-Host "  Frontend ($FrontendPort): Stopped" -ForegroundColor Red }
}

switch ($Action) {
    'start'            { Start-Services }
    'stop'             { Stop-Services }
    'restart'          { Stop-Services; Start-Sleep -Seconds 2; Start-Services }
    'status'           { Show-Status }
    'backend-start'    { Start-Backend }
    'backend-stop'     { Stop-Backend }
    'frontend-start'   { Start-Frontend }
    'frontend-stop'    { Stop-Frontend }
    default            { Write-Host "Unknown action: $Action" -ForegroundColor Red; Show-Help; exit 1 }
}
