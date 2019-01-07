import functools

from functools import lru_cache

from django.apps import apps


@lru_cache(maxsize=1)
def supported_models():
    app_config = apps.get_app_config("djangocms_navigation")
    try:
        extension = app_config.cms_extension
        return extension.navigation_apps_models
    except AttributeError:
        return app_config.navigation_apps_models


def is_model_supported(model):
    """Return bool value if model is in keys"""
    return model in supported_models().keys()


def get_supported_model_queryset(model):
    func = supported_models()[model]
    if func:
        return functools.partial(func, model)
