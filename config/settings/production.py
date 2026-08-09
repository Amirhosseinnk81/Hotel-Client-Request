"""
Production settings. Loaded when DJANGO_SETTINGS_MODULE=config.settings.production.

Not used yet in the current phase — kept in sync with base.py so the
project structure is ready for deployment work later (out of scope for now).
"""

from .base import *  # noqa: F401,F403

DEBUG = False

# In production ALLOWED_HOSTS must be explicitly set via the environment;
# base.py already reads it from ALLOWED_HOSTS with no permissive default here.

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
