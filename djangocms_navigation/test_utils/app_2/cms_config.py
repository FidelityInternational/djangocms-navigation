from cms.app_base import CMSAppConfig

from .models import TestModel3, TestModel4


class CMSApp2Config(CMSAppConfig):
    djangocms_navigation_enabled = True
    navigation_models = [TestModel3, TestModel4]
