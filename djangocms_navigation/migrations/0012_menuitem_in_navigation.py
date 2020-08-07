
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_navigation', '0011_menuitem_soft_root'),
    ]

    operations = [
        migrations.AddField(
            model_name='menuitem',
            name='in_navigation',
            field=models.BooleanField(db_index=True, default=True, verbose_name='in navigation'),
        ),
    ]
