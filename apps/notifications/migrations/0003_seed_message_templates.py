from django.db import migrations

# A copy (not an import) of services.DEFAULT_BODIES as they were when this
# migration was written — migrations must not depend on code that changes.
DEFAULTS = {
    "TICKET_CREATED": (
        "مهمان گرامی، درخواست «{title}» شما ثبت شد (شمارهٔ پیگیری {ticket_id}) "
        "و به واحد {department} سپرده شد. {hotel}"
    ),
    "TICKET_IN_PROGRESS": (
        "مهمان گرامی، همکار ما در واحد {department} رسیدگی به درخواست «{title}» را شروع کرد. {hotel}"
    ),
    "TICKET_RESOLVED": "مهمان گرامی، درخواست «{title}» شما توسط واحد {department} انجام شد. {hotel}",
    "TICKET_CANCELLED": (
        "مهمان گرامی، درخواست «{title}» (شمارهٔ {ticket_id}) لغو شد. "
        "در صورت نیاز با پذیرش تماس بگیرید. {hotel}"
    ),
}


def seed(apps, schema_editor):
    MessageTemplate = apps.get_model("notifications", "MessageTemplate")
    for event, body in DEFAULTS.items():
        MessageTemplate.objects.get_or_create(event=event, defaults={"body": body})


def unseed(apps, schema_editor):
    apps.get_model("notifications", "MessageTemplate").objects.filter(event__in=DEFAULTS).delete()


class Migration(migrations.Migration):
    """Start every event with an editable template holding the built-in text."""

    dependencies = [("notifications", "0002_message_templates")]

    operations = [migrations.RunPython(seed, unseed)]
