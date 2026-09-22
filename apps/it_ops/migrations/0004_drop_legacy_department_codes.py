from django.db import migrations, models


class Migration(migrations.Migration):
    """Drops the old code columns and puts the FKs under their names (see 0002)."""

    dependencies = [
        ("it_ops", "0003_copy_department_codes"),
    ]

    operations = [
        migrations.RemoveField(model_name="process", name="department"),
        migrations.RemoveField(model_name="departmentrequest", name="requesting_department"),
        migrations.RenameField(
            model_name="process", old_name="department_ref", new_name="department"
        ),
        migrations.RenameField(
            model_name="departmentrequest",
            old_name="requesting_department_ref",
            new_name="requesting_department",
        ),
        migrations.AlterModelOptions(
            name="project",
            options={"ordering": ["due_date", "title"]},
        ),
        migrations.AlterModelOptions(
            name="departmentrequest",
            options={"ordering": ["created_at"]},
        ),
        migrations.AlterModelOptions(
            name="task",
            options={"ordering": ["due_date", "created_at"]},
        ),
        migrations.AlterField(
            model_name="process",
            name="next_due_at",
            field=models.DateTimeField(
                blank=True,
                help_text=(
                    "Filled in automatically for recurring processes: last_done_at "
                    "(or creation) plus one period. May be moved by hand to postpone "
                    "a run; recalculated whenever the process is marked done or its "
                    "frequency changes."
                ),
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="roomdailystat",
            name="recorded_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
