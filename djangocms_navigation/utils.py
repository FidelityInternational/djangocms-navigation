from functools import lru_cache

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from cms.models import PageContent
from menus.menu_pool import menu_pool

from djangocms_versioning.constants import DRAFT, PUBLISHED
from djangocms_versioning.helpers import remove_published_where


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


def is_versioning_enabled(model):
    try:
        app_config = apps.get_app_config(model._meta.app_label).cms_config
    except LookupError:
        return False
    else:
        return app_config.djangocms_versioning_enabled


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


def is_preview_or_edit_mode(request):
    """
    Detemrine if the view is in the preview or edit mode.

    :param request: A request object
    :return: True if the view is the preview or edit mode, False if not.
    :rtype: Boolean
    """
    toolbar = getattr(request, "toolbar", None)
    if toolbar and (toolbar.edit_mode_active or toolbar.preview_mode_active):
        return True
    return False


def get_latest_page_content_for_page_grouper(obj, language):
    """
    Determine if the view is in the preview or edit mode.

    :param obj: A Page object
    :return: A queryset if an item exists, or None if not.
    :rtype: Queryset object, or None
    """
    page_contents = PageContent.objects.filter(
        page=obj,
        language=language,
        versions__state__in=[DRAFT, PUBLISHED]
    ).order_by("-versions__pk")
    return remove_published_where(page_contents).first()
