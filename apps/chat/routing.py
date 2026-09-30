"""
WebSocket routes. Only reachable when the server runs as ASGI with
CHAT_TRANSPORT=websocket — see consumers.py for the switch-on steps.
"""

from django.urls import path


def websocket_urlpatterns():
    # Imported lazily: channels is optional, and importing the consumer
    # on a WSGI deployment would make a missing dependency into a
    # startup crash for a feature that isn't even turned on.
    from .consumers import ChatConsumer

    return [path("ws/chat/<int:conversation_id>/", ChatConsumer.as_asgi())]
