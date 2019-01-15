from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.models import Page


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
                    "navigation configuration must be a Iterable object"
                )
        else:
            raise ImproperlyConfigured(
                "cms_config.py must have navigation_models attribute"
            )


class CoreCMSAppConfig(CMSAppConfig):
    djangocms_navigation_enabled = True
    navigation_models = {
        # model_class : field(s) to search in menu item form UI
        Page: ["title"]
    }
