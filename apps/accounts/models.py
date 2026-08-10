from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model. Every account in the system — guest or operator —
    is a row here, distinguished by `role`.

    Guests authenticate via national ID + phone (see apps.guests, Phase 5)
    and do not use a password (unusable password is set on creation).

    Operators and admins authenticate via username + password like a
    normal Django user.
    """

    class Role(models.TextChoices):
        GUEST = "GUEST", "Guest"
        OPERATOR = "OPERATOR", "Operator"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices)

    def __str__(self):
        return f"{self.username} ({self.role})"
