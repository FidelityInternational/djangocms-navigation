from functools import lru_cache

from django.apps import apps


@lru_cache(maxsize=1)
def supported_models():
    try:
        app_config = apps.get_app_config("djangocms_navigation")
        extension = app_config.cms_extension
        return extension.navigation_apps_models
    except LookupError:
        return []
