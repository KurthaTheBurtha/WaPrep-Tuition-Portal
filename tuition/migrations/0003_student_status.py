# Generated by Django 4.2.20 on 2025-05-09 19:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tuition', '0002_student_student_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active', max_length=20),
        ),
    ]
