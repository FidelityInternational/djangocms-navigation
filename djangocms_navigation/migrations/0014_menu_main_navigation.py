# Generated by Django 2.2.28 on 2022-08-10 04:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_navigation', '0013_auto_20200828_1000'),
    ]

    operations = [
        migrations.AddField(
            model_name='menu',
            name='main_navigation',
            field=models.BooleanField(default=False, verbose_name='Main Navigation'),
        ),
    ]
