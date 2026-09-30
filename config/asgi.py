"""
ASGI entry point.

Only used when the hotel switches CHAT_TRANSPORT to "websocket" and runs
the server as ASGI; the current Windows deployment is WSGI (config/wsgi.py)
and never loads this. HTTP keeps going through Django exactly as before —
the only thing ASGI adds here is the chat socket.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

django_asgi_app = get_asgi_application()

try:
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter

    from apps.chat.routing import websocket_urlpatterns

    application = ProtocolTypeRouter(
        {
            "http": django_asgi_app,
            "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns())),
        }
    )
except ImportError:
    # channels isn't installed: serve plain HTTP rather than refusing to
    # start over a feature that is switched off.
    application = django_asgi_app
