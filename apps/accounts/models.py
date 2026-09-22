from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model.

    Every account in the system — guest, operator, or admin —
    is represented by this model and distinguished by `role`.
    """

    class Role(models.TextChoices):
        GUEST = "GUEST", "Guest"
        OPERATOR = "OPERATOR", "Operator"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )

    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="operators",
    )

    # Deliberately no stored "available / busy" flag. Availability is
    # derived from assignments — busy while any assigned ticket is still
    # OPEN or IN_PROGRESS (apps.tickets.services.active_tickets_count) —
    # so it can never drift from reality the way the old manual toggle
    # could. The toggle's column was dropped in migration 0005.

    is_supervisor = models.BooleanField(
        default=False,
        help_text=(
            "A supervisor is still an OPERATOR in their department, with one "
            "extra authority: assigning tickets and setting priority. A flag "
            "rather than a separate role, so every existing operator check "
            "(department scoping, the colleagues list, who a ticket can be "
            "assigned to) keeps working unchanged, and a supervisor can "
            "still be assigned tickets themselves. Meaningless for "
            "GUEST/ADMIN roles."
        ),
    )

    def __str__(self):
        return f"{self.username} ({self.role})"