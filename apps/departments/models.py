from django.db import models


class Department(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    auto_assign = models.BooleanField(
        default=False,
        help_text=(
            "Hand each new guest ticket straight to the least-busy operator "
            "of this department who has the panel open. Off: new tickets "
            "wait for a supervisor to assign them."
        ),
    )

    working_hours = models.CharField(
        max_length=120,
        blank=True,
        help_text=(
            "Free text, e.g. «۰۸:۰۰ تا ۲۰:۰۰». Shown beside this "
            "department's numbers in the staff phone directory "
            "(apps/extensions), so whoever is about to ring knows "
            "whether anybody is there."
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return self.name