from collections import Iterable

from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppConfig, CMSAppExtension


class navigationCMSExtension(CMSAppExtension):

    def __init__(self):
        self.navigation_apps_models = []

    def configure_app(self, cms_config):
        if hasattr(cms_config, 'navigation_models'):
            navigation_app_models = getattr(cms_config, 'navigation_models')
            if isinstance(navigation_app_models, Iterable):
                self.navigation_apps_models.extend(navigation_app_models)
            else:
                raise ImproperlyConfigured(
                    "Navigation configuration must be a Iterable object")
        else:
            raise ImproperlyConfigured(
                "cms_config.py must have navigation_models attribute")


class CoreCMSAppConfig(CMSAppConfig):
    djangocms_navigation_enabled = True
    navigation_models = []
