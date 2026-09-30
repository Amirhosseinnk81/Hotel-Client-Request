"""
Base settings shared by all environments (development, production).

Environment-specific values (DEBUG, ALLOWED_HOSTS, DATABASE_URL, etc.)
are read from environment variables / a .env file — never hardcoded here.
"""

import importlib.util
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

# BASE_DIR points to backend/ (two levels up from config/settings/base.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_filters",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.guests",
    "apps.rooms",
    "apps.departments",
    "apps.tickets",
    "apps.it_ops",
    "apps.notifications",
    "apps.pms",
    "apps.iptv",
    "apps.extensions",
    "apps.chat",
    "apps.news",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database — configured per-environment (see development.py / production.py).
# Never SQLite for this project; PostgreSQL only.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Stage 2.8: local-disk ticket attachments — no S3/MinIO in this phase.
MAX_ATTACHMENT_SIZE_MB = config("MAX_ATTACHMENT_SIZE_MB", default=5, cast=int)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Guest login has no password, so this is the only real brake on
        # repeated national_id/room_number guessing. Tunable via env.
        "guest_login": config("GUEST_LOGIN_THROTTLE_RATE", default="10/min"),
        # The IPTV screens are read by set-top boxes, not people: a
        # sane ceiling costs the televisions nothing and limits how
        # fast anyone who got the key could sweep room numbers.
        "iptv": config("IPTV_THROTTLE_RATE", default="60/min"),
    },
}

# ---------------------------------------------------------------------------
# IT Ops
# ---------------------------------------------------------------------------
# IT staff are the OPERATORs of the department with this code (and the IT
# supervisor is the one with is_supervisor) — see apps/core/permissions.py.
IT_DEPARTMENT_CODE = config("IT_DEPARTMENT_CODE", default="IT")

# ---------------------------------------------------------------------------
# Live chat (apps/chat)
# ---------------------------------------------------------------------------
# How a chat message reaches the other side. "sse" (the default) needs
# nothing new: the Stage 3.2 stream already polls by cursor and carries
# chat as well as ticket events, on this WSGI server, with no Redis.
#
# "websocket" is written and tested but off until the hotel's server runs
# as ASGI — it adds "channels" to INSTALLED_APPS below and points
# ASGI_APPLICATION at config.asgi. See apps/chat/consumers.py for the
# four things switching it on needs.
CHAT_TRANSPORT = config("CHAT_TRANSPORT", default="sse")

# A WebSocket handshake can't carry an Authorization header and the access
# token must never ride in a URL, so the panel trades its token for a
# short-lived single-use ticket (apps/chat/tickets.py).
CHAT_TICKET_SECONDS = config("CHAT_TICKET_SECONDS", default=30, cast=int)

if CHAT_TRANSPORT == "websocket":
    INSTALLED_APPS = [*INSTALLED_APPS, "channels"]
    # daphne is the ASGI server, not the framework: listing it puts
    # `runserver` on ASGI in development. It is a deployment install, so
    # a missing daphne must not stop the app booting in websocket mode.
    if importlib.util.find_spec("daphne"):
        INSTALLED_APPS = ["daphne", *INSTALLED_APPS]
    ASGI_APPLICATION = "config.asgi.application"
    # In-memory works for a single process only; more than one worker
    # needs Redis (channels_redis), which is a deployment decision.
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": config(
                "CHANNEL_LAYER_BACKEND",
                default="channels.layers.InMemoryChannelLayer",
            ),
        }
    }
    redis_url = config("CHANNEL_LAYER_REDIS_URL", default="")
    if redis_url:
        CHANNEL_LAYERS["default"] = {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [redis_url]},
        }

# ---------------------------------------------------------------------------
# Staff phone directory (apps/extensions)
# ---------------------------------------------------------------------------
# Where the "take a backup" button writes its dated .xlsx. Point it at
# whatever actually gets copied off this machine; empty keeps it beside
# the code, so a backup is never silently lost because nobody set this.
EXTENSIONS_BACKUP_DIR = config("EXTENSIONS_BACKUP_DIR", default="")

# ---------------------------------------------------------------------------
# In-room television (Stage 3.4) — see apps/iptv
# ---------------------------------------------------------------------------
# Read-only: a guest can see their open requests and the hotel's
# information on the TV, but files nothing from a remote control.
#
# The API (/api/v1/iptv/rooms/<room>/) is called by the IPTV middleware's
# server and proves itself with X-IPTV-Key; empty key = refused, so an
# unconfigured integration is never left open.
IPTV_SHARED_KEY = config("IPTV_SHARED_KEY", default="")
# The page (/tv/<room>/) is opened by the television itself, which can't
# send headers. It is protected by where the request comes from and/or a
# signature in the URL; with neither set the page is refused. Both set =
# both must pass. Behind a proxy, REMOTE_ADDR must be the real client
# address (nginx real_ip) — X-Forwarded-For is not trusted.
IPTV_ALLOWED_NETWORKS = config("IPTV_ALLOWED_NETWORKS", default="")
IPTV_PAGE_SECRET = config("IPTV_PAGE_SECRET", default="")
IPTV_PAGE_REFRESH_SECONDS = config("IPTV_PAGE_REFRESH_SECONDS", default=30, cast=int)
IPTV_BASE_URL = config("IPTV_BASE_URL", default="")

# ---------------------------------------------------------------------------
# PMS integration (Stage 3.3) — see apps/pms
# ---------------------------------------------------------------------------
# The hotel runs Harris (هریس), which has no public API documentation: the
# endpoint, the credential and the exact field names come from Harris
# support. Everything below is settings so that adapting to them doesn't
# need a code change.
#
# Inbound (the PMS calls us at POST /api/v1/pms/events/): with no
# PMS_SHARED_KEY the endpoint refuses everything, so an unconfigured
# integration is never left open. PMS_HMAC_SECRET is optional; setting it
# makes a valid signature mandatory.
PMS_SHARED_KEY = config("PMS_SHARED_KEY", default="")
PMS_HMAC_SECRET = config("PMS_HMAC_SECRET", default="")
# Outbound (we ask the PMS, `manage.py pull_pms`). The default client reads
# a JSON file, so the whole flow works before Harris grants API access.
PMS_CLIENT = config("PMS_CLIENT", default="apps.pms.client.FilePmsClient")
PMS_EVENTS_FILE = config("PMS_EVENTS_FILE", default="")
PMS_BASE_URL = config("PMS_BASE_URL", default="")
PMS_EVENTS_PATH = config("PMS_EVENTS_PATH", default="/events")
PMS_API_KEY = config("PMS_API_KEY", default="")
PMS_AUTH_HEADER = config("PMS_AUTH_HEADER", default="Authorization: Bearer {key}")
PMS_SINCE_PARAM = config("PMS_SINCE_PARAM", default="since")
PMS_ITEMS_PATH = config("PMS_ITEMS_PATH", default="")
# Their JSON field names -> ours, when they differ (dotted paths), and their
# event names -> ours. Defaults in apps/pms/services.py.
PMS_FIELD_MAP = {}
PMS_EVENT_MAP = {}

# ---------------------------------------------------------------------------
# Operator presence, auto-assignment and live notifications (Stage 3.2)
# ---------------------------------------------------------------------------
# An operator counts as "on shift" for auto-assignment while their panel has
# been seen within this many seconds (the live stream beats every
# SSE_HEARTBEAT_SECONDS, so keep this comfortably above that).
OPERATOR_PRESENCE_SECONDS = config("OPERATOR_PRESENCE_SECONDS", default=120, cast=int)
# Live stream (GET /operator/events/): how often it checks for new tickets,
# how often it sends a heartbeat, and after how long it ends so the browser
# reconnects with a fresh access token. Each open stream holds one server
# thread for its lifetime — size the production server's thread pool to
# the number of operators logged in at once, plus headroom.
SSE_POLL_SECONDS = config("SSE_POLL_SECONDS", default=2, cast=float)
SSE_HEARTBEAT_SECONDS = config("SSE_HEARTBEAT_SECONDS", default=25, cast=float)
SSE_MAX_SECONDS = config("SSE_MAX_SECONDS", default=300, cast=float)

# ---------------------------------------------------------------------------
# SMS (Stage 3.1) — see apps/notifications
# ---------------------------------------------------------------------------
# Messages are queued in the database and sent by `send_pending_sms`
# (Windows Task Scheduler, every minute). The console backend only logs.
SMS_ENABLED = config("SMS_ENABLED", default=True, cast=bool)
SMS_BACKEND = config("SMS_BACKEND", default="apps.notifications.backends.ConsoleSmsBackend")
SMS_API_KEY = config("SMS_API_KEY", default="")
SMS_SENDER = config("SMS_SENDER", default="")
SMS_HOTEL_NAME = config("SMS_HOTEL_NAME", default="هتل")
SMS_MAX_ATTEMPTS = config("SMS_MAX_ATTEMPTS", default=5, cast=int)

# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_TOKEN_LIFETIME", default=15, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_TOKEN_LIFETIME", default=7, cast=int)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------------------------------------------------------------------------
# drf-spectacular (OpenAPI / Swagger / ReDoc)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Hotel Client Request Platform API",
    "DESCRIPTION": "API for managing hotel guest requests and operator workflows.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "RoomStatusEnum": "apps.rooms.models.Room.Status",
        "TicketStatusEnum": "apps.tickets.models.Ticket.Status",
        # Tickets and IT Ops both have a "priority" field with different
        # choice sets; name them so the schema doesn't fall back to hashes.
        "TicketPriorityEnum": "apps.tickets.models.Ticket.Priority",
        "ITPriorityEnum": "apps.it_ops.models.Priority",
        "ITProcessStatusEnum": "apps.it_ops.models.Process.Status",
        "ITProjectStatusEnum": "apps.it_ops.models.Project.Status",
        "ITRequestStatusEnum": "apps.it_ops.models.DepartmentRequest.Status",
        "ITGoalStatusEnum": "apps.it_ops.models.Goal.Status",
        "ITTaskStatusEnum": "apps.it_ops.models.Task.Status",
        # Chat threads and news items both have a "kind"; name both, or
        # spectacular resolves the collision with a hashed name.
        "ChatKindEnum": "apps.chat.models.Conversation.Kind",
        "NewsKindEnum": "apps.news.models.NewsItem.Kind",
        "NewsAudienceEnum": "apps.news.models.NewsItem.Audience",
    },
}

# ---------------------------------------------------------------------------
# CORS — tightened per environment
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())
# Required for the browser to send/receive the httpOnly refresh-token cookie
# on cross-origin requests (frontend and backend run on different ports/
# subdomains). CORS_ALLOWED_ORIGINS must stay an explicit list (never "*")
# for this to be honored by the browser.
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# JWT refresh-token cookie (see apps/core/jwt_cookies.py)
# ---------------------------------------------------------------------------
# False only makes sense for local HTTP development; must be True (the
# default) anywhere real, since browsers refuse to store Secure cookies set
# over plain HTTP anyway — this only ever needs overriding to False in a
# local .env.
JWT_COOKIE_SECURE = config("JWT_COOKIE_SECURE", default=not DEBUG, cast=bool)

# ---------------------------------------------------------------------------
# Logging — INFO/WARNING/ERROR/CRITICAL, no sensitive data (see section 24)
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": config("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}