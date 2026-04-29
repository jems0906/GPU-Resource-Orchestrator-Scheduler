param(
    [int]$BackendPort = 8011,
    [int]$FrontendPort = 5174,
    [int]$PostgresPort = 5543,
    [string]$PythonPath = 'C:\temp\gpu_orchestrator_py311\Scripts\python.exe',
    [string]$FrontendMirror = 'C:\temp\gpu_orchestrator_frontend'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $repoRoot 'backend'
$frontendRoot = Join-Path $repoRoot 'frontend'
$viteScript = Join-Path $FrontendMirror 'node_modules\vite\bin\vite.js'

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-PortListening {
    param([int]$Port)
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    return $null -ne $listener
}

function Stop-PortProcess {
    param([int]$Port)
    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($processId in $listeners) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
        } catch {
            Write-Warning "Failed to stop PID $processId on port ${Port}: $($_.Exception.Message)"
        }
    }
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [hashtable]$Headers = @{},
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $null = Invoke-WebRequest -Uri $Url -Headers $Headers -UseBasicParsing -TimeoutSec 5
            return $true
        } catch {
            Start-Sleep -Milliseconds 750
        }
    }

    return $false
}

function Ensure-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Write-Step 'Checking prerequisites'
Ensure-Command 'docker'
Ensure-Command 'node'

if (-not (Test-Path $PythonPath)) {
    throw "Python runtime not found: $PythonPath"
}

if (-not (Test-Path $FrontendMirror)) {
    throw "Frontend mirror not found: $FrontendMirror"
}

if (-not (Test-Path $viteScript)) {
    throw "Vite script not found: $viteScript"
}

Write-Step 'Ensuring dependency containers are running'
$postgresContainer = docker ps -a --format '{{.Names}}' | Select-String '^gpu-orch-postgres$'
if ($postgresContainer) {
    docker start gpu-orch-postgres | Out-Null
} else {
    Write-Warning 'Container gpu-orch-postgres was not found. Start PostgreSQL manually on port 5543 if needed.'
}

$redisContainer = docker ps -a --format '{{.Names}}' | Select-String '^gpuresourceorchestratorscheduler-redis-1$'
if ($redisContainer) {
    docker start gpuresourceorchestratorscheduler-redis-1 | Out-Null
} else {
    Write-Warning 'Container gpuresourceorchestratorscheduler-redis-1 was not found. Start Redis manually on port 6379 if needed.'
}

Write-Step 'Stopping stale backend/frontend listeners'
Stop-PortProcess -Port $BackendPort
Stop-PortProcess -Port $FrontendPort

$backendLog = Join-Path $env:TEMP 'gpu-orchestrator-backend.log'
$backendErrorLog = Join-Path $env:TEMP 'gpu-orchestrator-backend-error.log'
$frontendLog = Join-Path $env:TEMP 'gpu-orchestrator-frontend.log'
$frontendErrorLog = Join-Path $env:TEMP 'gpu-orchestrator-frontend-error.log'

Write-Step 'Starting backend'
$backendCommand = @(
    "`$env:DATABASE_URL='postgresql+asyncpg://gpu_user:gpu_password@127.0.0.1:$PostgresPort/gpu_orchestrator'",
    "`$env:REDIS_URL='redis://127.0.0.1:6379/0'",
    "`$env:SECRET_KEY='dev-secret-key-change-in-production'",
    "`$env:API_KEY='dev-api-key-change-in-production'",
    "Set-Location '$backendRoot'",
    "& '$PythonPath' -m uvicorn app.main:app --host 0.0.0.0 --port $BackendPort"
) -join '; '

$backendProcess = Start-Process -FilePath 'powershell.exe' `
    -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $backendCommand) `
    -RedirectStandardOutput $backendLog `
    -RedirectStandardError $backendErrorLog `
    -WindowStyle Hidden `
    -PassThru

if (-not (Wait-HttpOk -Url "http://localhost:$BackendPort/health" -TimeoutSeconds 60)) {
    throw "Backend did not become healthy. Check log: $backendLog"
}

Write-Step 'Syncing frontend source into temp mirror'
Copy-Item (Join-Path $frontendRoot 'src') -Destination $FrontendMirror -Recurse -Force
Copy-Item (Join-Path $frontendRoot 'vite.config.ts') -Destination $FrontendMirror -Force

Write-Step 'Building frontend preview bundle'
Push-Location $FrontendMirror
try {
    & node $viteScript build --outDir dist
} finally {
    Pop-Location
}

Write-Step 'Starting frontend preview'
$frontendCommand = @(
    "Set-Location '$FrontendMirror'",
    "& node '$viteScript' preview '$FrontendMirror' --config '$FrontendMirror\vite.config.ts' --strictPort --port $FrontendPort --host 0.0.0.0"
) -join '; '

$frontendProcess = Start-Process -FilePath 'powershell.exe' `
    -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $frontendCommand) `
    -RedirectStandardOutput $frontendLog `
    -RedirectStandardError $frontendErrorLog `
    -WindowStyle Hidden `
    -PassThru

if (-not (Wait-HttpOk -Url "http://localhost:$FrontendPort/" -TimeoutSeconds 60)) {
    throw "Frontend preview did not become ready. Check log: $frontendLog"
}

Write-Step 'Startup complete'
Write-Host "Backend:  http://localhost:$BackendPort/health"
Write-Host "Frontend: http://localhost:$FrontendPort/"
Write-Host "Backend PID:  $($backendProcess.Id)"
Write-Host "Frontend PID: $($frontendProcess.Id)"
Write-Host "Backend log:  $backendLog"
Write-Host "Backend err:  $backendErrorLog"
Write-Host "Frontend log: $frontendLog"
Write-Host "Frontend err: $frontendErrorLog"