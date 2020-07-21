# Generated by Django 2.2.13 on 2020-07-20 07:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_navigation', '0010_auto_20200630_0402'),
    ]

    operations = [
        migrations.AddField(
            model_name='menuitem',
            name='soft_root',
            field=models.BooleanField(db_index=True, default=False, help_text='All ancestors will not be displayed in the navigation', verbose_name='soft root'),
        ),
    ]
