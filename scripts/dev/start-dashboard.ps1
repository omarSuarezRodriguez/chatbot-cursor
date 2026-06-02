# Inicia el dashboard Django en el puerto 8000 (requiere PostgreSQL).
. "$PSScriptRoot\common.ps1"

param(
    [switch]$SkipMigrate
)

Write-DevInfo "Iniciando dashboard..."
Assert-Command -Name "python" -FixHint "Instala Python 3.11+ desde https://www.python.org/downloads/"
Assert-Command -Name "docker" -FixHint "PostgreSQL local usa Docker: https://www.docker.com/products/docker-desktop/"

$py = Assert-Venv
Assert-DashboardDependencies -PythonExe $py
$hasDashboardEnv = Test-EnvFile -RelativePath ".env.dashboard" -ExamplePath ".env.dashboard.example" -Label "configuración del dashboard"

if (-not $hasDashboardEnv) {
    Write-DevWarn "Continuando sin .env.dashboard (Django usará valores por defecto de settings)."
}

Test-DockerDaemon

# Asegurar que PostgreSQL está arriba
$dbRunning = $false
Push-Location (Get-ProjectRoot)
try {
    $containerId = (& docker compose ps -q db 2>$null | Select-Object -First 1)
    if ($containerId) {
        & docker compose exec -T db pg_isready -U dashboard -d dashboard 2>$null | Out-Null
        $dbRunning = ($LASTEXITCODE -eq 0)
    }
} catch {
    $dbRunning = $false
} finally {
    Pop-Location
}

if (-not $dbRunning) {
    Write-DevInfo "PostgreSQL no está activo; iniciándolo..."
    & "$PSScriptRoot\start-db.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (Test-PortListening -Port 8000) {
    Write-DevWarn "El puerto 8000 ya está en uso. Si el dashboard ya corre, no hace falta reiniciarlo."
    Show-ServiceUrls
    exit 0
}

if (-not $SkipMigrate) {
    Write-DevInfo "Aplicando migraciones Django..."
    $migrateCode = Invoke-ProjectPython -PythonArgs @("dashboard/manage.py", "migrate", "--noinput")
    if ($migrateCode -ne 0) {
        Write-DevErr "migrate falló. ¿PostgreSQL accesible en localhost:5432?"
        Write-Host "  → Verifica .env.dashboard (DATABASE_URL) y ejecuta: .\dev.cmd db" -ForegroundColor Yellow
        exit $migrateCode
    }
}

Show-ServiceUrls
Write-DevOk "Arrancando Django en http://localhost:8000 ..."
Write-Host "  Primera vez: python dashboard/manage.py createsuperuser" -ForegroundColor Gray
Write-Host "  Detener: Ctrl+C en esta ventana" -ForegroundColor Gray
Write-Host ""

$exitCode = Invoke-ProjectPython -PythonArgs @("dashboard/manage.py", "runserver", "8000")
exit $exitCode
