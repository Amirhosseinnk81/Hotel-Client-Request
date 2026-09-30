from django.urls import path

from .views import (
    ChatConfigView,
    ConversationListView,
    MarkReadView,
    MessageListCreateView,
    SocketTicketView,
    StartConversationView,
    UnreadCountView,
)

app_name = "chat"

urlpatterns = [
    path("chat/config/", ChatConfigView.as_view(), name="config"),
    path("chat/unread/", UnreadCountView.as_view(), name="unread"),
    path("chat/socket-ticket/", SocketTicketView.as_view(), name="socket-ticket"),
    path("chat/conversations/", ConversationListView.as_view(), name="conversations"),
    path("chat/conversations/start/", StartConversationView.as_view(), name="start"),
    path("chat/conversations/<int:pk>/messages/", MessageListCreateView.as_view(), name="messages"),
    path("chat/conversations/<int:pk>/read/", MarkReadView.as_view(), name="read"),
]
