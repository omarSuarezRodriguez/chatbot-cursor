"""Django settings for the local admin dashboard."""
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import whitenoise  # noqa: F401
except Exception:
    HAS_WHITENOISE = False
else:
    HAS_WHITENOISE = True


def _load_env_file(path: Path) -> None:
    _load_env_file_with_policy(path, override_loaded=False)


_loaded_from_files: set[str] = set()


def _load_env_file_with_policy(path: Path, *, override_loaded: bool) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key in os.environ and key not in _loaded_from_files:
            # Respect environment injected by hosting/provider.
            continue
        if key in _loaded_from_files and not override_loaded:
            continue
        os.environ[key] = value
        _loaded_from_files.add(key)


_load_env_file_with_policy(PROJECT_ROOT / ".env.unified", override_loaded=False)
_load_env_file(PROJECT_ROOT / ".env")
_load_env_file_with_policy(PROJECT_ROOT / ".env.dashboard", override_loaded=True)


def _database_from_url(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 5432),
    }


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-local-dev-only")
DEBUG = os.environ.get("DJANGO_DEBUG", os.environ.get("DEBUG", "0")) == "1"
_allowed_hosts_raw = os.environ.get(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,testserver",
)
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_raw.split(",") if h.strip()]
_csrf_trusted_origins_raw = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").strip()
if _csrf_trusted_origins_raw:
    CSRF_TRUSTED_ORIGINS = [
        origin.strip()
        for origin in _csrf_trusted_origins_raw.split(",")
        if origin.strip()
    ]
else:
    CSRF_TRUSTED_ORIGINS = [
        f"https://{host}"
        for host in ALLOWED_HOSTS
        if host not in {"localhost", "127.0.0.1", "testserver"}
    ] + [
        f"http://{host}"
        for host in ALLOWED_HOSTS
        if host not in {"localhost", "127.0.0.1", "testserver"}
    ]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
_secure_cookies_default = "0" if DEBUG else "1"
CSRF_COOKIE_SECURE = os.environ.get("DJANGO_CSRF_COOKIE_SECURE", _secure_cookies_default) == "1"
SESSION_COOKIE_SECURE = os.environ.get("DJANGO_SESSION_COOKIE_SECURE", _secure_cookies_default) == "1"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.operations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if HAS_WHITENOISE:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.dashboard_flags",
                "config.context_processors.dashboard_roles",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

_database_url = os.environ.get("DATABASE_URL", "").strip()
if _database_url:
    DATABASES = {"default": _database_from_url(_database_url)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "data" / "dashboard.sqlite3"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
if HAS_WHITENOISE:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

BOT_HEALTH_URL = os.environ.get("BOT_HEALTH_URL", "http://127.0.0.1:5000/health")
DASHBOARD_ENABLE_WRITES = os.environ.get("DASHBOARD_ENABLE_WRITES", "0") == "1"
RESTAURANT_NAME = os.environ.get("RESTAURANT_NAME", "La Casa del Sabor")

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/mipanel/"
LOGOUT_REDIRECT_URL = "/login/"
