import os

from log_outgoing_requests.datastructures import ContentType
from log_outgoing_requests.formatters import HttpFormatter

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = "so-secret-i-cant-believe-you-are-looking-at-this"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "log_outgoing_requests.db"),
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.admin",
    "solo",
    "log_outgoing_requests",
    "testapp",
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

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "outgoing_requests": {"()": HttpFormatter},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
        },
        "log_outgoing_requests": {
            "level": "DEBUG",
            "formatter": "outgoing_requests",
            "class": "logging.StreamHandler",
        },
        "save_outgoing_requests": {
            "level": "DEBUG",
            "class": "log_outgoing_requests.handlers.DatabaseOutgoingRequestsHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "requests": {
            "handlers": ["log_outgoing_requests", "save_outgoing_requests"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

#
# LOG OUTGOING REQUESTS
#
LOG_OUTGOING_REQUESTS_DB_SAVE = True
LOG_OUTGOING_REQUESTS_DB_SAVE_BODY = True
LOG_OUTGOING_REQUESTS_CONTENT_TYPES = [
    ContentType(pattern="application/json", default_encoding="utf-8"),
    ContentType(pattern="application/soap+xml", default_encoding="utf-8"),
    ContentType(pattern="application/xml", default_encoding="utf-8"),
    ContentType(pattern="text/xml", default_encoding="iso-8859-1"),
    ContentType(pattern="text/*", default_encoding="utf-8"),
]
LOG_OUTGOING_REQUESTS_EMIT_BODY = True
LOG_OUTGOING_REQUESTS_MAX_CONTENT_LENGTH = 524_288  # 0.5 MB


ROOT_URLCONF = "testapp.urls"
ALLOWED_HOSTS = ["*"]
USE_TZ = True

DEBUG = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

PRIVATE_MEDIA_ROOT = os.path.join(BASE_DIR, "private-media")
PRIVATE_MEDIA_URL = "/private-media/"
