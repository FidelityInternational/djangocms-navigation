from unittest.mock import Mock

from django.core.exceptions import ImproperlyConfigured

from cms import app_registration
from cms.models import Page
from cms.utils.setup import setup_cms_apps

from djangocms_navigation.cms_config import NavigationCMSExtension
from djangocms_navigation.test_utils.app_1.models import TestModel1, TestModel2
from djangocms_navigation.test_utils.app_2.models import TestModel3, TestModel4
from djangocms_navigation.utils import supported_models

from .utils import TestCase


class AppRegistrationTestCase(TestCase):
    def test_missing_cms_config(self):
        extensions = NavigationCMSExtension()
        cms_config = Mock(
            djangocms_navigation_enabled=True, app_config=Mock(label="blah_cms_config")
        )

        with self.assertRaises(ImproperlyConfigured):
            extensions.configure_app(cms_config)

    def test_invalid_cms_config_parameter(self):
        extensions = NavigationCMSExtension()
        cms_config = Mock(
            djangocms_navigation_enabled=True,
            navigation_models=23234,
            app_config=Mock(label="blah_cms_config"),
        )

        with self.assertRaises(ImproperlyConfigured):
            extensions.configure_app(cms_config)

    def test_valid_cms_config_parameter(self):
        extensions = NavigationCMSExtension()
        cms_config = Mock(
            djangocms_navigation_enabled=True,
            navigation_models=[TestModel1, TestModel2, TestModel3, TestModel4],
            app_config=Mock(label="blah_cms_config"),
        )

        with self.assertNotRaises(ImproperlyConfigured):
            extensions.configure_app(cms_config)
            register_model = []
            for model in extensions.navigation_apps_models:
                register_model.append(model)

            self.assertTrue(TestModel1 in register_model)
            self.assertTrue(TestModel2 in register_model)
            self.assertTrue(TestModel3 in register_model)
            self.assertTrue(TestModel4 in register_model)


class NavigationIntegrationTestCase(TestCase):
    def setUp(self):
        app_registration.get_cms_extension_apps.cache_clear()
        app_registration.get_cms_config_apps.cache_clear()

    def test_config_with_multiple_apps(self):
        setup_cms_apps()
        registered_models = supported_models()

        expected_models = [TestModel1, TestModel2, TestModel3, TestModel4, Page]

        self.assertCountEqual(registered_models, expected_models)
