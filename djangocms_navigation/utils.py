from functools import lru_cache

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from menus.menu_pool import menu_pool

from .models import MenuContent


def get_admin_name(model, name):
    name = '{}_{}_{}'.format(
        model._meta.app_label,
        model._meta.model_name,
        name
    )
    return name


# FIXME: Reuse the django cms reverse util: admin_reverse()
def reverse_admin_name(model, name, args=None, kwargs=None):
    name = get_admin_name(model, name)
    url = reverse('admin:{}'.format(name), args=args, kwargs=kwargs)
    return url


def get_select2_url_name(content_model=MenuContent):
    url_name = "{}_select2_content_object".format(
        content_model._meta.app_label
    )
    return url_name


def _get_app_config(app_label):
    """
    An internal utility to get the app config from a supplied model
    """
    try:
        app_config = apps.get_app_config(app_label)
    except LookupError:
        return {}
    return app_config


def _in_reuse_mode(app_config):
    """
    Determine if the navigation package is being reused / extended by another package
    """
    return getattr(app_config, 'navigation_app_shared_mode', False)


@lru_cache(maxsize=1)
def supported_models(model=MenuContent):
    app_config = _get_app_config(model._meta.app_label)
    # Fall back to the current apps configuration
    if not _in_reuse_mode(app_config):
        app_config = _get_app_config("djangocms_navigation")
    # If the app config is not defined, return an empty dictionary
    if not app_config:
        return app_config
    extension = app_config.cms_extension
    return extension.navigation_apps_models


@lru_cache(maxsize=1)
def supported_content_type_pks(model=MenuContent):
    app_config = _get_app_config(model._meta.app_label)
    # Fall back to the current apps configuration
    if not _in_reuse_mode(app_config):
        app_config = _get_app_config("djangocms_navigation")
    models = app_config.cms_extension.navigation_apps_models
    content_type_dict = ContentType.objects.get_for_models(*models)
    return [ct.pk for ct in content_type_dict.values()]


@lru_cache(maxsize=1)
def is_model_supported(model):
    """Return bool value if model is in supported_models"""
    return model in supported_models(model).keys()


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
