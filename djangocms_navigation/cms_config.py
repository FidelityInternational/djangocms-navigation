from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.models import Page

from djangocms_versioning.datastructures import VersionableItem

from .models import MenuContent, MenuItem


class NavigationCMSExtension(CMSAppExtension):
    def __init__(self):
        self.navigation_apps_models = {}

    def configure_app(self, cms_config):
        if hasattr(cms_config, "navigation_models"):
            navigation_app_models = getattr(cms_config, "navigation_models")
            if isinstance(navigation_app_models, dict):
                self.navigation_apps_models.update(navigation_app_models)
            else:
                raise ImproperlyConfigured(
                    "navigation configuration must be a dictionary object"
                )
        else:
            raise ImproperlyConfigured(
                "cms_config.py must have navigation_models attribute"
            )


def copy_menu_content(original_content):
    """Copy the MenuContent object and deepcopy its menu items."""
    # Copy root menu item
    original_root = original_content.root
    root_fields = {
        field.name: getattr(original_root, field.name)
        for field in MenuItem._meta.fields
        if field.name not in [MenuItem._meta.pk.name, "path", "depth"]
    }
    new_root = MenuItem.add_root(**root_fields)

    # Copy MenuContent object
    content_fields = {
        field.name: getattr(original_content, field.name)
        for field in MenuContent._meta.fields
        if field.name not in [MenuContent._meta.pk.name, "root"]
    }
    content_fields["root"] = new_root
    new_content = MenuContent.objects.create(**content_fields)

    # Copy menu items
    to_create = []
    for item in MenuItem.get_tree(original_root).exclude(pk=original_root.pk):
        item_fields = {
            field.name: getattr(item, field.name)
            for field in MenuItem._meta.fields
            if field.name not in [MenuItem._meta.pk.name, "path"]
        }
        item_fields["path"] = new_root.path + item.path[MenuItem.steplen:]
        to_create.append(MenuItem(**item_fields))
    MenuItem.objects.bulk_create(to_create)

    return new_content


class NavigationCMSAppConfig(CMSAppConfig):
    djangocms_navigation_enabled = getattr(
        settings, "DJANGOCMS_NAVIGATION_CMS_MODELS_ENABLED", True
    )
    djangocms_versioning_enabled = getattr(
        settings, "DJANGOCMS_NAVIGATION_VERSIONING_ENABLED", True
    )
    navigation_models = {
        # model_class : field(s) to search in menu item form UI
        Page: ["title"]
    }
    versioning = [
        VersionableItem(
            content_model=MenuContent,
            grouper_field_name="menu",
            copy_function=copy_menu_content,
        )
    ]
