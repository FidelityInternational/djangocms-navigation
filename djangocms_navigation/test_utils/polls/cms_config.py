from cms.app_base import CMSAppConfig

from .models import PollContent


class PollsCMSConfig(CMSAppConfig):
    djangocms_navigation_enabled = True
    navigation_models = {
        PollContent: ["text"]
    }
