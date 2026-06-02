# Inicia el bot Flask (Waitress) en el puerto 5000.
. "$PSScriptRoot\common.ps1"

Write-DevInfo "Iniciando bot..."
Assert-Command -Name "python" -FixHint "Instala Python 3.11+ desde https://www.python.org/downloads/"

$py = Assert-Venv
Assert-BotDependencies -PythonExe $py
Test-EnvFile -RelativePath ".env" -ExamplePath ".env.example" -Label "configuración del bot" | Out-Null

if (Test-PortListening -Port 5000) {
    Write-DevWarn "El puerto 5000 ya está en uso. Si el bot ya corre, no hace falta reiniciarlo."
    Show-ServiceUrls
    exit 0
}

Show-ServiceUrls
Write-DevOk "Arrancando Waitress en http://localhost:5000 ..."
Write-Host "  Detener: Ctrl+C en esta ventana" -ForegroundColor Gray
Write-Host ""

$exitCode = Invoke-ProjectPython -PythonArgs @("run.py")
exit $exitCode
