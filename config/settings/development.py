"""
Development settings. Loaded when DJANGO_SETTINGS_MODULE=config.settings.development.

Runs directly on the host (no Docker) against a local PostgreSQL 16 instance.
"""

from .base import *  # noqa: F401,F403

DEBUG = True

# CORS is wide open in local development only.
CORS_ALLOW_ALL_ORIGINS = True
