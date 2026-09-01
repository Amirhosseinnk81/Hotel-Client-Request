import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('departments', '0001_initial'),
        ('tickets', '0007_category_sla_minutes'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='guest_rating',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5),
                ],
                help_text='1-5 stars, set once by the guest after the ticket is RESOLVED.',
            ),
        ),
        migrations.AddField(
            model_name='ticket',
            name='guest_feedback',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='ticket',
            name='reopened_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text=(
                    'Set the one time (if ever) a guest reopens this ticket. '
                    'Presence of a value — not just the current status — is '
                    'what blocks a second reopen, so the limit holds even if '
                    'the ticket gets resolved again afterwards.'
                ),
            ),
        ),
        migrations.CreateModel(
            name='QuickRequestTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                (
                    'icon',
                    models.CharField(
                        help_text=(
                            "A lucide-react icon name (e.g. 'Droplet', "
                            "'Shirt', 'Bell') — the frontend renders this "
                            "icon on the card. Not validated here; an "
                            "unknown name just falls back to a generic icon."
                        ),
                        max_length=50,
                    ),
                ),
                ('is_active', models.BooleanField(default=True)),
                (
                    'order',
                    models.PositiveIntegerField(
                        default=0,
                        help_text='Lower numbers show first on the guest form.',
                    ),
                ),
                (
                    'category',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='quick_templates',
                        to='tickets.category',
                    ),
                ),
                (
                    'department',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='quick_templates',
                        to='departments.department',
                    ),
                ),
            ],
            options={
                'ordering': ['order', 'title'],
            },
        ),
    ]
