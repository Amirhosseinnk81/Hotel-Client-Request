from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_is_available"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_supervisor",
            field=models.BooleanField(
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
            ),
        ),
    ]
