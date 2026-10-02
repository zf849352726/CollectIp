import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    "COLLECTIP_SECRET_KEY",
    "collectip-local-development-only-key-change-before-production-2026",
)
DEBUG = os.getenv("COLLECTIP_DEBUG", "true").lower() in {"1", "true", "yes"}
SECURE_MODE = os.getenv("COLLECTIP_SECURE", "false").lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("COLLECTIP_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "proxy_web",
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

ROOT_URLCONF = "webapp.urls"
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
            ],
        },
    }
]
WSGI_APPLICATION = "webapp.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("COLLECTIP_DB_PATH", BASE_DIR / "db.sqlite3"),
    }
}

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/admin/login/"
SECURE_SSL_REDIRECT = SECURE_MODE
SESSION_COOKIE_SECURE = SECURE_MODE
CSRF_COOKIE_SECURE = SECURE_MODE
SECURE_HSTS_SECONDS = int(os.getenv("COLLECTIP_HSTS_SECONDS", "31536000")) if SECURE_MODE else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_MODE
SECURE_HSTS_PRELOAD = SECURE_MODE
if SECURE_MODE:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
PROXY_CHECK_URLS = [
    url.strip()
    for url in os.getenv(
        "COLLECTIP_CHECK_URLS",
        "http://httpbin.org/ip,https://api.ipify.org?format=json,https://icanhazip.com",
    ).split(",")
    if url.strip()
]
PROXY_CHECK_TIMEOUT = int(os.getenv("COLLECTIP_CHECK_TIMEOUT", "8"))

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "collectip.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "standard",
        }
    },
    "loggers": {"proxy_web": {"handlers": ["file"], "level": "INFO", "propagate": True}},
}
