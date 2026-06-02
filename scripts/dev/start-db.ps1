# Inicia PostgreSQL local (Docker Compose).
. "$PSScriptRoot\common.ps1"

Write-DevInfo "Iniciando PostgreSQL..."
Assert-Command -Name "docker" -FixHint "Instala Docker Desktop: https://www.docker.com/products/docker-desktop/"
Test-DockerDaemon

if (-not (Test-Path (Join-Path (Get-ProjectRoot) "docker-compose.yml"))) {
    Write-DevErr "No se encontró docker-compose.yml en la raíz del proyecto."
    exit 1
}

Invoke-Compose -ComposeArgs @("up", "-d", "db")
Wait-PostgresReady

Write-DevOk "Base de datos lista."
Write-Host "  Conexión: postgresql://dashboard:dashboard@localhost:5432/dashboard" -ForegroundColor Gray
Write-Host "  Detener:  .\dev.cmd stop   (o: docker compose down)" -ForegroundColor Gray
