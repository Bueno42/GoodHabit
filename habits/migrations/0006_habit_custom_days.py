from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('habits', '0005_habit_category_habit_duration_days'),
    ]

    operations = [
        migrations.AddField(
            model_name='habit',
            name='custom_days',
            field=models.JSONField(
                blank=True,
                default=list,
                verbose_name='Días de frecuencia personalizada',
            ),
        ),
    ]
