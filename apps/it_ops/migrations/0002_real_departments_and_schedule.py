import django.db.models.deletion
from django.db import migrations, models

# The old private department list (see 0001), kept only for these columns.
LEGACY_CHOICES = [('IT', 'IT'), ('FRONT_DESK', 'Front Desk'), ('HOUSEKEEPING', 'Housekeeping'), ('MAINTENANCE', 'Maintenance'), ('F_AND_B', 'Food & Beverage'), ('SALES', 'Sales'), ('HR', 'HR'), ('FINANCE', 'Finance'), ('MANAGEMENT', 'Management'), ('OTHER', 'Other')]


class Migration(migrations.Migration):
    """
    - Process.department / DepartmentRequest.requesting_department: from a
      private copy of the department list (TextChoices) to a real FK to
      departments.Department, so there is one list of departments in the
      whole system. Existing values are carried over by code.
    - Orderings no longer sort Priority strings alphabetically (that put
      MEDIUM first and CRITICAL last); priority order is applied in the
      views with priority_rank().
    - Process.next_due_at is now calculated (help text only here — the
      logic is in Process.save()); RoomDailyStat.recorded_at becomes
      "last computed".
    """

    dependencies = [
        ("departments", "0001_initial"),
        ("it_ops", "0001_initial"),
    ]

    operations = [
        # The old code columns become nullable before 0004 drops them, so
        # that rolling back re-creates them as nullable and 0003's reverse
        # can fill them in; rolling back further restores NOT NULL.
        migrations.AlterField(
            model_name="process",
            name="department",
            field=models.CharField(choices=LEGACY_CHOICES, default="IT", max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name="departmentrequest",
            name="requesting_department",
            field=models.CharField(choices=LEGACY_CHOICES, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="process",
            name="department_ref",
            field=models.ForeignKey(
                blank=True,
                help_text="The hotel department this process serves (blank = IT itself).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="it_processes",
                to="departments.department",
            ),
        ),
        migrations.AddField(
            model_name="departmentrequest",
            name="requesting_department_ref",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="it_requests",
                to="departments.department",
            ),
        ),
    ]
