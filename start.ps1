
$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$Frontend = Join-Path $Root "frontend"

Write-Host "`n=== Logistics Management System ===" -ForegroundColor Cyan

# 1. Check project files
if (-not (Test-Path (Join-Path $Root "backend/server.py"))) {
    throw "Missing backend/server.py"
}

if (-not (Test-Path (Join-Path $Frontend "package.json"))) {
    throw "Missing frontend/package.json"
}

# 2. Check Python
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher not found. Install Python 3 first."
}

py -3 --version
if ($LASTEXITCODE -ne 0) {
    throw "Python 3 is unavailable."
}

# 3. Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js is not installed."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is not installed."
}

$NodeVersion = node -p "process.versions.node"
if ([version]$NodeVersion -lt [version]"22.12.0") {
    throw "Node.js 22.12.0 or later is required."
}

# 4. Install frontend dependencies when needed
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    if (-not (Test-Path (Join-Path $Frontend "package-lock.json"))) {
        throw "Missing frontend/package-lock.json"
    }

    Write-Host "Installing frontend dependencies..."
    Push-Location $Frontend
    try {
        npm ci
        if ($LASTEXITCODE -ne 0) {
            throw "npm ci failed."
        }
    }
    finally {
        Pop-Location
    }
}

# 5. Start backend in a separate PowerShell window
Write-Host "Starting backend..."

Start-Process -FilePath "powershell.exe" `
    -WorkingDirectory $Root `
    -ArgumentList @("-NoExit", "-Command", "py -3 backend/server.py")

# 6. Wait for backend health check
$BackendReady = $false

for ($i = 0; $i -lt 30; $i++) {
    try {
        $Response = Invoke-WebRequest `
            -Uri "http://127.0.0.1:8000/api/health" `
            -TimeoutSec 2

        if ($Response.StatusCode -eq 200) {
            $BackendReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $BackendReady) {
    throw "Backend did not become ready. Check port 8000 and the backend window."
}

# 7. Start frontend in a separate PowerShell window
Write-Host "Starting frontend..."

Start-Process -FilePath "powershell.exe" `
    -WorkingDirectory $Frontend `
    -ArgumentList @("-NoExit", "-Command", "npm run dev")

# 8. Wait for frontend
$FrontendReady = $false

for ($i = 0; $i -lt 30; $i++) {
    try {
        $Response = Invoke-WebRequest `
            -Uri "http://localhost:3000" `
            -TimeoutSec 2

        if ($Response.StatusCode -eq 200) {
            $FrontendReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $FrontendReady) {
    throw "Frontend did not become ready. Check the frontend window."
}

# 9. Open application
Start-Process "http://localhost:3000"

Write-Host "`nStartup successful!" -ForegroundColor Green
Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend:  http://localhost:8000/api/health"
Write-Host "Keep both server windows open."
