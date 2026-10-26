#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$PythonExecutable = $env:PYTHON,
    [switch]$SkipInstall,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$FrontendDirectory = Join-Path $ProjectRoot 'frontend'
$LogDirectory = Join-Path $ProjectRoot 'output/startup'

function Resolve-Python {
    if ($PythonExecutable) { $Candidates = @($PythonExecutable) }
    else { $Candidates = @('py.exe', 'python.exe', 'python3.exe') }
    foreach ($Candidate in $Candidates) {
        $Command = Get-Command $Candidate -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $Command) { continue }
        $PythonArguments = @()
        if ($Command.Name -eq 'py.exe') { $PythonArguments += '-3' }
        try {
            # Resolve the real interpreter, so the tracked process is not a launcher.
            $Executable = & $Command.Source @PythonArguments -c 'import sys; assert sys.version_info.major == 3; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $Executable -and (Test-Path -LiteralPath $Executable -PathType Leaf)) {
                return $Executable
            }
        }
        catch { continue }
    }
    throw 'Python 3 is unavailable. Install it or pass -PythonExecutable C:\path\to\python.exe.'
}

function Assert-FreePort([int]$Port) {
    $Listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try {
        $Listener.Server.ExclusiveAddressUse = $true
        $Listener.Start()
    }
    catch { throw "Port $Port is already in use. Stop the existing service before starting this application." }
    finally { $Listener.Stop() }
}

function Assert-Running($Process, [string]$Name) {
    $Process.Refresh()
    if ($Process.HasExited) {
        throw "$Name exited during startup. Check $LogDirectory for its output and error logs."
    }
}

function Wait-Ready($Process, [string]$Name, [string]$Uri, [scriptblock]$Validate) {
    $Deadline = [DateTime]::UtcNow.AddSeconds(30)
    while ([DateTime]::UtcNow -lt $Deadline) {
        Assert-Running $Process $Name
        $Ready = $false
        try {
            # Basic parsing avoids Internet Explorer and interactive HTML parsing prompts in Windows PowerShell.
            $Response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 2
            $Ready = $Response.StatusCode -eq 200 -and (& $Validate $Response.Content)
        }
        catch { $Ready = $false }
        if ($Ready) {
            Assert-Running $Process $Name
            return
        }
        Start-Sleep -Milliseconds 250
    }
    throw "$Name did not become ready at $Uri. Check $LogDirectory."
}

function Stop-OwnedProcess($Process) {
    if ($null -eq $Process) { return }
    try {
        $Process.Refresh()
        if (-not $Process.HasExited) {
            # Kill only the process tree created by this invocation (including Vite's helpers).
            & "$env:SystemRoot\System32\taskkill.exe" /PID $Process.Id /T /F 2>$null | Out-Null
            $Process.WaitForExit(5000) | Out-Null
        }
    }
    finally { $Process.Dispose() }
}

Write-Host 'Logistics Management System - local Windows development'
foreach ($RelativePath in @('backend/server.py', 'frontend/package.json', 'frontend/package-lock.json')) {
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot $RelativePath) -PathType Leaf)) {
        throw "Missing $RelativePath"
    }
}
$PythonPath = Resolve-Python
$NodeCommand = Get-Command node.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1
$NpmCommand = Get-Command npm.cmd -CommandType Application -ErrorAction Stop | Select-Object -First 1
$NodeVersion = & $NodeCommand.Source -p 'process.versions.node'
if ($LASTEXITCODE -ne 0 -or [version]$NodeVersion -lt [version]'22.12.0') {
    throw 'Node.js 22.12.0 or later is required.'
}

# Refuse occupied ports before modifying dependencies or starting either server.
Assert-FreePort 8000
Assert-FreePort 3000
if (-not $SkipInstall) {
    Write-Host 'Installing locked frontend dependencies...'
    Push-Location $FrontendDirectory
    try {
        & $NpmCommand.Source ci
        if ($LASTEXITCODE -ne 0) { throw 'npm ci failed; no servers were started.' }
    }
    finally { Pop-Location }
}
$ViteScript = Join-Path $FrontendDirectory 'node_modules/vite/bin/vite.js'
if (-not (Test-Path -LiteralPath $ViteScript -PathType Leaf)) {
    throw 'Vite is missing. Run again without -SkipInstall.'
}
# Check again after installation in case another service started in the meantime.
Assert-FreePort 8000
Assert-FreePort 3000
New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
$LogPrefix = Join-Path $LogDirectory ([Guid]::NewGuid().ToString('N'))
$BackendProcess = $null
$FrontendProcess = $null
$PreviousHost = $env:LMS_HOST
$PreviousApiBase = $env:VITE_API_BASE_URL
try {
    # This command starts a local pair; keep the Vite proxy and backend on the same address.
    $env:LMS_HOST = '127.0.0.1'
    $env:VITE_API_BASE_URL = '/api'
    $BackendScript = Join-Path $ProjectRoot 'backend/server.py'
    $BackendProcess = Start-Process -FilePath $PythonPath -WorkingDirectory $ProjectRoot `
        -ArgumentList @('-u', ('"{0}"' -f $BackendScript)) -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput "$LogPrefix-backend.log" -RedirectStandardError "$LogPrefix-backend-error.log"
    Write-Host "Backend PID: $($BackendProcess.Id)"
    $HealthCheck = {
        param($Content)
        $Health = $Content | ConvertFrom-Json
        $Health.status -eq 'ok' -and $Health.service -eq 'lms-backend'
    }
    Wait-Ready $BackendProcess 'Backend' 'http://127.0.0.1:8000/api/health' $HealthCheck

    $FrontendProcess = Start-Process -FilePath $NodeCommand.Source -WorkingDirectory $FrontendDirectory `
        -ArgumentList @(('"{0}"' -f $ViteScript), '--host', '127.0.0.1', '--port', '3000', '--strictPort') `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput "$LogPrefix-frontend.log" `
        -RedirectStandardError "$LogPrefix-frontend-error.log"
    Write-Host "Frontend PID: $($FrontendProcess.Id)"
    Wait-Ready $FrontendProcess 'Frontend' 'http://127.0.0.1:3000' {
        param($Content)
        $Content -match '/src/main.tsx' -and $Content -match 'id="root"'
    }
    Wait-Ready $FrontendProcess 'Frontend API proxy' 'http://127.0.0.1:3000/api/health' $HealthCheck
    Assert-Running $BackendProcess 'Backend'
    Assert-Running $FrontendProcess 'Frontend'
    if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:3000' }
    Write-Host 'Startup successful!' -ForegroundColor Green
    Write-Host 'Frontend: http://127.0.0.1:3000'
    Write-Host 'Backend:  http://127.0.0.1:8000/api/health'
    Write-Host "Logs: $LogPrefix-*.log"
    Read-Host 'Press Enter to stop both servers (Ctrl+C also stops them)' | Out-Null
}
finally {
    # Restore the caller's environment even if startup or cleanup fails.
    $env:LMS_HOST = $PreviousHost
    $env:VITE_API_BASE_URL = $PreviousApiBase
    try { Stop-OwnedProcess $FrontendProcess }
    finally { Stop-OwnedProcess $BackendProcess }
}
