# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.db import migrations

from cms.utils.i18n import get_default_language_for_site

logger = logging.getLogger(__name__)


def add_navigation_languages(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    MenuContent = apps.get_model("djangocms_navigation", "MenuContent")
    navigation_queryset = MenuContent.objects.using(db_alias).filter(language__exact="")
    for model in navigation_queryset:
        model.language = get_default_language_for_site(model.site)
        model.save()
        logger.info(
            "Added default language {} to model {}".format(
                model.language, model.__str__()
            )
        )


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_navigation', '0008_menucontent_language'),
    ]
    operations = [
        migrations.RunPython(
            add_navigation_languages
        )
    ]
