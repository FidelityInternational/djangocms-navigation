from functools import lru_cache

from django.apps import apps
from django.contrib.contenttypes.models import ContentType

from menus.menu_pool import menu_pool


@lru_cache(maxsize=1)
def supported_models():
    try:
        app_config = apps.get_app_config("djangocms_navigation")
    except LookupError:
        return {}
    else:
        extension = app_config.cms_extension
        return extension.navigation_apps_models


@lru_cache(maxsize=1)
def supported_content_type_pks():
    app_config = apps.get_app_config("djangocms_navigation")
    models = app_config.cms_extension.navigation_apps_models
    content_type_dict = ContentType.objects.get_for_models(*models)
    return [ct.pk for ct in content_type_dict.values()]


@lru_cache(maxsize=1)
def is_model_supported(model):
    """Return bool value if model is in supported_models"""
    return model in supported_models().keys()


def get_versionable_for_content(content):
    try:
        from djangocms_versioning import versionables
    except ImportError:
        return
    try:
        return versionables.for_content(content)
    except KeyError:
        return


def purge_menu_cache(site_id=None, language=None):
    menu_pool.clear(site_id=site_id, language=language)
