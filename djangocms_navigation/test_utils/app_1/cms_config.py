from cms.app_base import CMSAppConfig
from .models import TestModel1, TestModel2


class CMSApp1Config(CMSAppConfig):
    djangocms_navigation_enabled = True
    navigation_models = [TestModel1, TestModel2]
