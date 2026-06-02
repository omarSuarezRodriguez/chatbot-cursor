# Punto de entrada: db | bot | dashboard | all | stop
param(
    [Parameter(Position = 0)]
    [ValidateSet("db", "bot", "dashboard", "all", "stop")]
    [string]$Command = "all"
)

$scriptDir = $PSScriptRoot
switch ($Command) {
    "db" { & "$scriptDir\start-db.ps1"; exit $LASTEXITCODE }
    "bot" { & "$scriptDir\start-bot.ps1"; exit $LASTEXITCODE }
    "dashboard" { & "$scriptDir\start-dashboard.ps1"; exit $LASTEXITCODE }
    "all" { & "$scriptDir\start-all.ps1"; exit $LASTEXITCODE }
    "stop" { & "$scriptDir\stop-all.ps1"; exit $LASTEXITCODE }
}
