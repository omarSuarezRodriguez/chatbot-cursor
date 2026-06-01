import os

from app.app import app

if __name__ == "__main__":
    from waitress import serve

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    print(f"Serving on http://{host}:{port} (waitress)")
    serve(app, host=host, port=port)
