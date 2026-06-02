import os
import subprocess
import sys

from app.app import app


def run_server() -> None:
    from waitress import serve

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    print(f"Serving bot on http://{host}:{port} (waitress)")
    serve(app, host=host, port=port)


if __name__ == "__main__":
    if "--serve" in sys.argv:
        run_server()
    else:
        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)
        command = (
            f'start "" cmd /k "cd /d ""{script_dir}"" && python ""{script_path}"" --serve"'
        )
        subprocess.Popen(command, shell=True)
        print("Opened a new CMD window running the bot.")
