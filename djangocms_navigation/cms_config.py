from functools import partial

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.models import Page

from .utils import purge_menu_cache
from .models import MenuContent
from .models import MenuItem


class NavigationCMSExtension(CMSAppExtension):
    def __init__(self):
        self.navigation_apps_models = {}

    def configure_app(self, cms_config):
        if not hasattr(cms_config, "navigation_models"):
            raise ImproperlyConfigured(
                "cms_config.py must have navigation_models attribute"
            )

        navigation_app_models = getattr(cms_config, "navigation_models")
        if isinstance(navigation_app_models, dict):
            self.navigation_apps_models.update(navigation_app_models)
        else:
            raise ImproperlyConfigured(
                "navigation configuration must be a dictionary object"
            )


def _copy_menu_content(menu_model, item_model, original_content):
    """Use this function together with a partial to customize the models"""

    original_root = original_content.root
    root_fields = {
        field.name: getattr(original_root, field.name)
        for field in item_model._meta.fields
        if field.name not in [item_model._meta.pk.name, "path", "depth"]
    }
    new_root = item_model.add_root(**root_fields)

    # Copy MenuContent object
    content_fields = {
        field.name: getattr(original_content, field.name)
        for field in menu_model._meta.fields
        if field.name not in [menu_model._meta.pk.name, "root"]
    }
    content_fields["root"] = new_root
    new_content = menu_model.objects.create(**content_fields)

    # Copy menu items
    to_create = []
    for item in item_model.get_tree(original_root).exclude(pk=original_root.pk):
        item_fields = {
            field.name: getattr(item, field.name)
            for field in item_model._meta.fields
            if field.name not in [item_model._meta.pk.name, "path"]
        }
        item_fields["path"] = new_root.path + item.path[item_model.steplen:]
        to_create.append(item_model(**item_fields))
    item_model.objects.bulk_create(to_create)

    return new_content


complete_copy_menu_content = partial(
    _copy_menu_content,
    MenuContent,
    MenuItem
)


def copy_menu_content(original_content):
    """Copy the MenuContent object and deepcopy its menu items."""
    return complete_copy_menu_content(original_content)


def on_menu_content_publish(version):
    menu_content = version.content
    purge_menu_cache(site_id=menu_content.menu.site_id)


def on_menu_content_unpublish(version):
    menu_content = version.content
    purge_menu_cache(site_id=menu_content.menu.site_id)


def on_menu_content_draft_create(version):
    menu_content = version.content
    purge_menu_cache(site_id=menu_content.menu.site_id)


def on_menu_content_archive(version):
    menu_content = version.content
    purge_menu_cache(site_id=menu_content.menu.site_id)


class NavigationCMSAppConfig(CMSAppConfig):
    djangocms_navigation_enabled = getattr(
        settings, "DJANGOCMS_NAVIGATION_CMS_MODELS_ENABLED", True
    )
    djangocms_versioning_enabled = getattr(
        settings, "DJANGOCMS_NAVIGATION_VERSIONING_ENABLED", True
    )
    djangocms_moderation_enabled = getattr(
        settings, "DJANGOCMS_NAVIGATION_MODERATION_ENABLED", True
    )
    navigation_models = {
        # model_class : field(s) to search in menu item form UI
        Page: ["title"]
    }
    if djangocms_versioning_enabled:
        from djangocms_versioning.datastructures import VersionableItem

        versioning = [
            VersionableItem(
                content_model=MenuContent,
                grouper_field_name="menu",
                copy_function=complete_copy_menu_content,
                preview_url=MenuContent.get_preview_url,
                on_publish=on_menu_content_publish,
                on_unpublish=on_menu_content_unpublish,
                on_draft_create=on_menu_content_draft_create,
                on_archive=on_menu_content_archive,
            )
        ]
    moderated_models = [MenuContent]
