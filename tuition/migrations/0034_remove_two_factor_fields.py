# Generated manually to remove 2FA fields

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tuition', '0033_add_phone_number_and_2fa_method'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='two_factor_enabled',
        ),
        migrations.RemoveField(
            model_name='user',
            name='two_factor_setup_complete',
        ),
        migrations.RemoveField(
            model_name='user',
            name='phone_number',
        ),
        migrations.RemoveField(
            model_name='user',
            name='two_factor_method',
        ),
    ] 