"""SQLite settings for dashboard unit tests (no PostgreSQL required)."""

from config.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / ".test.sqlite3",
    }
}
