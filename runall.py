"""
Arranque local en un solo comando: PostgreSQL (Docker), migraciones, bot, dashboard y ngrok.

Uso (desde la raíz del proyecto):
    python runall.py

No modifica lógica del bot ni del dashboard; solo abre procesos en ventanas nuevas.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BOT_PORT = 5000
DASH_PORT = 8000


def _find_python() -> Path:
    for rel in (
        ROOT / "venv" / "Scripts" / "python.exe",
        Path.home() / "Desktop" / "Chatbot cursor" / "venv" / "Scripts" / "python.exe",
    ):
        if rel.is_file():
            return rel
    return Path(sys.executable)


def _port_in_use(port: int) -> bool:
    try:
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        return False


def _run(cmd: list[str], *, check: bool = False) -> int:
    print(f"  → {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=ROOT, check=check).returncode


def _spawn_console(title: str, command: list[str]) -> None:
    """Abre una ventana cmd que permanece abierta."""
    py = command[0]
    args = " ".join(f'"{a}"' if " " in a else a for a in command[1:])
    inner = f'"{py}" {args}' if args else f'"{py}"'
    subprocess.Popen(
        f'start "{title}" cmd /k {inner}',
        cwd=ROOT,
        shell=True,
    )


def _ensure_env_dashboard() -> None:
    dst = ROOT / ".env.dashboard"
    src = ROOT / ".env.dashboard.example"
    if not dst.exists() and src.exists():
        shutil.copy(src, dst)
        print("  → Copiado .env.dashboard desde .env.dashboard.example")


def _start_postgres() -> None:
    if _port_in_use(5432):
        print("[runall] PostgreSQL ya escucha en :5432 (Docker o instalación local).")
        return
    if not shutil.which("docker"):
        print("[runall] AVISO: sin Docker y sin PG en :5432. Instala Docker o inicia PostgreSQL.")
        return
    code = _run(["docker", "compose", "up", "-d", "db"])
    if code != 0:
        print("[runall] AVISO: docker compose up db falló. ¿Docker Desktop en ejecución?")
        return
    print("[runall] Esperando PostgreSQL…")
    for _ in range(45):
        if _port_in_use(5432):
            print("[runall] PostgreSQL listo.")
            return
        time.sleep(2)
    print("[runall] AVISO: PostgreSQL no respondió a tiempo en :5432.")


def _migrate(python: Path) -> None:
    code = _run([str(python), "dashboard/manage.py", "migrate", "--noinput"])
    if code != 0:
        sys.exit(code)


def main() -> None:
    python = _find_python()
    print(f"[runall] Python: {python}")
    print(f"[runall] Raíz:   {ROOT}\n")

    _ensure_env_dashboard()
    _start_postgres()
    _migrate(python)

    if not _port_in_use(BOT_PORT):
        print("[runall] Iniciando bot (puerto 5000)…")
        _spawn_console("Bot Flask", [str(python), "run.py"])
    else:
        print("[runall] Bot ya en puerto 5000.")

    if not _port_in_use(DASH_PORT):
        print("[runall] Iniciando dashboard (puerto 8000)…")
        _spawn_console(
            "Dashboard Django",
            [str(python), "dashboard/manage.py", "runserver", str(DASH_PORT)],
        )
    else:
        print("[runall] Dashboard ya en puerto 8000.")

    ngrok = shutil.which("ngrok")
    if ngrok:
        print("[runall] Iniciando ngrok http 5000…")
        _spawn_console("ngrok", [ngrok, "http", str(BOT_PORT)])
    else:
        print("[runall] AVISO: ngrok no está en PATH. Instálalo para webhook Twilio en local.")

    time.sleep(2)
    webbrowser.open(f"http://localhost:{DASH_PORT}/accounts/login/")

    print("\n=== URLs ===")
    print(f"  Dashboard:  http://localhost:{DASH_PORT}/")
    print(f"  Login:      http://localhost:{DASH_PORT}/accounts/login/")
    print(f"  Admin:      http://localhost:{DASH_PORT}/admin/")
    print(f"  Bot health: http://localhost:{BOT_PORT}/health")
    print(f"  Webhook:    POST http://localhost:{BOT_PORT}/bot")
    print("  Twilio:     usa la URL https de la ventana ngrok + /bot")
    print("\n[runall] Ventanas abiertas: Bot, Dashboard, ngrok (si aplica).")
    print("[runall] Login staff: usuario admin / contraseña 1234 (si lo creaste).")
    print("[runall] Cierra las ventanas cmd o usa: .\\dev.cmd stop")


if __name__ == "__main__":
    main()
