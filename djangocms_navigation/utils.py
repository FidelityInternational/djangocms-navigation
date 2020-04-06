from functools import lru_cache

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from menus.menu_pool import menu_pool


def get_admin_name(model, name):
    name = '{}_{}_{}'.format(
        model._meta.app_label,
        model._meta.model_name,
        name
    )
    return name


def reverse_admin_name(model, name, args=None, kwargs=None):
    name = get_admin_name(model, name)
    url = reverse('admin:{}'.format(name), args=args, kwargs=kwargs)
    return url


@lru_cache(maxsize=1)
def supported_models(model):
    try:
        app_config = apps.get_app_config(model._meta.app_label)
    except LookupError:
        return {}
    else:
        extension = app_config.cms_extension
        return extension.navigation_apps_models


@lru_cache(maxsize=1)
def supported_content_type_pks(model):
    app_config = apps.get_app_config(model._meta.app_label)
    models = app_config.cms_extension.navigation_apps_models
    content_type_dict = ContentType.objects.get_for_models(*models)
    return [ct.pk for ct in content_type_dict.values()]


@lru_cache(maxsize=1)
def is_model_supported(app_model, model):
    """Return bool value if model is in supported_models"""
    return model in supported_models(app_model).keys()


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
