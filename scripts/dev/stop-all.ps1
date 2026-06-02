# Detiene PostgreSQL y libera puertos 5000/8000 (bot y dashboard).
. "$PSScriptRoot\common.ps1"

Write-DevInfo "Deteniendo entorno local..."

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Push-Location (Get-ProjectRoot)
    try {
        & docker compose down 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-DevOk "PostgreSQL detenido (docker compose down)."
        }
    } catch {
        Write-DevWarn "No se pudo ejecutar docker compose down."
    } finally {
        Pop-Location
    }
} else {
    Write-DevWarn "Docker no disponible; omitiendo PostgreSQL."
}

Stop-PortListeners -Ports @(5000, 8000)

Write-DevOk "Servicios locales detenidos."
Write-Host "  Para borrar datos de PostgreSQL: docker compose down -v" -ForegroundColor Gray
