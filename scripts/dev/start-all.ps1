# Inicia PostgreSQL, bot y dashboard (bot y dashboard en ventanas nuevas).
. "$PSScriptRoot\common.ps1"

Write-DevInfo "Comprobando dependencias..."
Assert-Command -Name "python" -FixHint "Instala Python 3.11+"
Assert-Command -Name "docker" -FixHint "Instala Docker Desktop"
Test-DockerDaemon

$py = Assert-Venv
Assert-BotDependencies -PythonExe $py
Assert-DashboardDependencies -PythonExe $py
Test-EnvFile -RelativePath ".env" -ExamplePath ".env.example" -Label "configuración del bot" | Out-Null
Test-EnvFile -RelativePath ".env.dashboard" -ExamplePath ".env.dashboard.example" -Label "configuración del dashboard" | Out-Null

if (Test-PortListening -Port 5000) {
    Write-DevWarn "Puerto 5000 ocupado; omitiendo arranque del bot."
} else {
    Assert-PortFree -Port 5000 -ServiceName "bot"
}

if (Test-PortListening -Port 8000) {
    Write-DevWarn "Puerto 8000 ocupado; omitiendo arranque del dashboard."
} else {
    Assert-PortFree -Port 8000 -ServiceName "dashboard"
}

Write-DevInfo "1/3 PostgreSQL..."
& "$PSScriptRoot\start-db.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-DevInfo "2/3 Migraciones Django..."
$migrateCode = Invoke-ProjectPython -PythonArgs @("dashboard/manage.py", "migrate", "--noinput")
if ($migrateCode -ne 0) {
    Write-DevErr "migrate falló."
    exit $migrateCode
}

$botScript = (Resolve-Path "$PSScriptRoot\start-bot.ps1").Path
$dashScript = (Resolve-Path "$PSScriptRoot\start-dashboard.ps1").Path

if (-not (Test-PortListening -Port 5000)) {
    Write-DevInfo "3/3 Abriendo bot y dashboard en ventanas nuevas..."
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $botScript
    ) | Out-Null
    Start-Sleep -Seconds 1
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $dashScript, "-SkipMigrate"
    ) | Out-Null
} elseif (-not (Test-PortListening -Port 8000)) {
    Write-DevInfo "3/3 Abriendo solo dashboard..."
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $dashScript, "-SkipMigrate"
    ) | Out-Null
} else {
    Write-DevOk "Bot y dashboard ya estaban en ejecución."
}

Show-ServiceUrls
Write-DevOk "Entorno local iniciado."
Write-Host "  Detener todo: .\dev.cmd stop" -ForegroundColor Gray
Write-Host "  O cierra las ventanas del bot/dashboard y ejecuta stop para PostgreSQL." -ForegroundColor Gray
