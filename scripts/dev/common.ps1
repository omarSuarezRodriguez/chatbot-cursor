# Funciones compartidas para arranque local (bot + dashboard + PostgreSQL).
$ErrorActionPreference = "Stop"

$script:ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

function Get-ProjectRoot {
    return $script:ProjectRoot
}

function Write-DevInfo {
    param([string]$Message)
    Write-Host "[dev] $Message" -ForegroundColor Cyan
}

function Write-DevOk {
    param([string]$Message)
    Write-Host "[dev] $Message" -ForegroundColor Green
}

function Write-DevWarn {
    param([string]$Message)
    Write-Host "[dev] AVISO: $Message" -ForegroundColor Yellow
}

function Write-DevErr {
    param([string]$Message)
    Write-Host "[dev] ERROR: $Message" -ForegroundColor Red
}

function Assert-Command {
    param(
        [string]$Name,
        [string]$FixHint
    )
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-DevErr "'$Name' no está instalado o no está en el PATH."
        if ($FixHint) { Write-Host "  → $FixHint" -ForegroundColor Yellow }
        exit 1
    }
}

function Test-DockerDaemon {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-DevErr "Docker no responde. ¿Está Docker Desktop en ejecución?"
        Write-Host "  → Inicia Docker Desktop y vuelve a ejecutar el comando." -ForegroundColor Yellow
        exit 1
    }
}

function Get-VenvPython {
    $root = Get-ProjectRoot
    foreach ($rel in @("venv\Scripts\python.exe", ".venv\Scripts\python.exe")) {
        $path = Join-Path $root $rel
        if (Test-Path $path) { return $path }
    }
    return $null
}

function Assert-Venv {
    $py = Get-VenvPython
    if (-not $py) {
        Write-DevErr "No se encontró el entorno virtual (venv o .venv)."
        Write-Host "  → Desde la raíz del proyecto:" -ForegroundColor Yellow
        Write-Host "       python -m venv venv" -ForegroundColor Yellow
        Write-Host "       .\venv\Scripts\activate" -ForegroundColor Yellow
        Write-Host "       pip install -r requirements.txt -r requirements-dashboard.txt" -ForegroundColor Yellow
        exit 1
    }
    return $py
}

function Test-PythonModule {
    param(
        [string]$PythonExe,
        [string]$ModuleName
    )
    & $PythonExe -c "import $ModuleName" 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Assert-BotDependencies {
    param([string]$PythonExe)
    $missing = @()
    foreach ($mod in @("flask", "waitress", "twilio")) {
        if (-not (Test-PythonModule -PythonExe $PythonExe -ModuleName $mod)) {
            $missing += $mod
        }
    }
    if ($missing.Count -gt 0) {
        Write-DevErr "Faltan dependencias del bot: $($missing -join ', ')"
        Write-Host "  → pip install -r requirements.txt" -ForegroundColor Yellow
        exit 1
    }
}

function Assert-DashboardDependencies {
    param([string]$PythonExe)
    if (-not (Test-PythonModule -PythonExe $PythonExe -ModuleName "django")) {
        Write-DevErr "Django no está instalado."
        Write-Host "  → pip install -r requirements-dashboard.txt" -ForegroundColor Yellow
        exit 1
    }
}

function Test-EnvFile {
    param(
        [string]$RelativePath,
        [string]$ExamplePath,
        [string]$Label
    )
    $path = Join-Path (Get-ProjectRoot) $RelativePath
    if (-not (Test-Path $path)) {
        Write-DevWarn "No existe $Label ($RelativePath)."
        $example = Join-Path (Get-ProjectRoot) $ExamplePath
        if (Test-Path $example) {
            Write-Host "  → copy $ExamplePath $RelativePath" -ForegroundColor Yellow
        }
        return $false
    }
    return $true
}

function Test-PortListening {
    param([int]$Port)
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        return ($null -ne $conn -and $conn.Count -gt 0)
    } catch {
        return $false
    }
}

function Assert-PortFree {
    param(
        [int]$Port,
        [string]$ServiceName
    )
    if (Test-PortListening -Port $Port) {
        Write-DevErr "El puerto $Port ya está en uso ($ServiceName)."
        Write-Host "  → Cierra el proceso que lo usa o ejecuta: .\dev.cmd stop" -ForegroundColor Yellow
        exit 1
    }
}

function Invoke-Compose {
    param([string[]]$ComposeArgs)
    Push-Location (Get-ProjectRoot)
    try {
        & docker compose @ComposeArgs
        if ($LASTEXITCODE -ne 0) {
            Write-DevErr "docker compose falló: docker compose $($ComposeArgs -join ' ')"
            exit $LASTEXITCODE
        }
    } finally {
        Pop-Location
    }
}

function Wait-PostgresReady {
    param([int]$TimeoutSeconds = 90)
    Write-DevInfo "Esperando PostgreSQL (hasta ${TimeoutSeconds}s)..."
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    Push-Location (Get-ProjectRoot)
    try {
        while ((Get-Date) -lt $deadline) {
            & docker compose exec -T db pg_isready -U dashboard -d dashboard 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-DevOk "PostgreSQL listo en localhost:5432"
                return
            }
            Start-Sleep -Seconds 2
        }
        Write-DevErr "PostgreSQL no respondió a tiempo."
        Write-Host "  → Revisa: docker compose logs db" -ForegroundColor Yellow
        exit 1
    } finally {
        Pop-Location
    }
}

function Show-ServiceUrls {
    Write-Host ""
    Write-Host "=== URLs del entorno local ===" -ForegroundColor Cyan
    Write-Host "  Bot (webhook):  http://localhost:5000/bot"
    Write-Host "  Health:         http://localhost:5000/health"
    Write-Host "  Dashboard:      http://localhost:8000/"
    Write-Host "  Login staff:    http://localhost:8000/accounts/login/"
    Write-Host "  Django admin:   http://localhost:8000/admin/"
    Write-Host ""
}

function Invoke-ProjectPython {
    param([string[]]$PythonArgs)
    $py = Assert-Venv
    Push-Location (Get-ProjectRoot)
    try {
        & $py @PythonArgs
        return $LASTEXITCODE
    } finally {
        Pop-Location
    }
}

function Stop-PortListeners {
    param([int[]]$Ports)
    foreach ($port in $Ports) {
        try {
            $pids = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($procId in $pids) {
                if ($procId -and $procId -gt 0) {
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                    Write-DevInfo "Proceso en puerto $port detenido (PID $procId)."
                }
            }
        } catch {
            Write-DevWarn "No se pudo liberar el puerto $port automáticamente."
        }
    }
}
