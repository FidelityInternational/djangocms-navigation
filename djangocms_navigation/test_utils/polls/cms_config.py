from cms.app_base import CMSAppConfig
from cms.models import Page

from .models import PollContent


class PollsCMSConfig(CMSAppConfig):
    djangocms_navigation_enabled = True
    navigation_models = {Page: ["title"], PollContent: ["text"]}
