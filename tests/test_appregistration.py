import imp
from unittest.mock import Mock, patch

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings, TestCase

from cms import app_registration
from cms.models import Page
from cms.utils.setup import configure_cms_apps, setup_cms_apps

from djangocms_navigation import cms_config
from djangocms_navigation.models import MenuContent
from djangocms_navigation.test_utils.app_1.models import TestModel1, TestModel2
from djangocms_navigation.test_utils.app_2.models import TestModel3, TestModel4
from djangocms_navigation.test_utils.polls.models import PollContent
from djangocms_navigation.utils import supported_models

from .utils import UsefulAssertsMixin


class AppRegistrationTestCase(TestCase, UsefulAssertsMixin):
    def test_missing_cms_config(self):
        extensions = cms_config.NavigationCMSExtension()
        config = Mock(
            djangocms_navigation_enabled=True, app_config=Mock(label="blah_cms_config")
        )

        with self.assertRaises(ImproperlyConfigured):
            extensions.configure_app(config)

    def test_invalid_cms_config_parameter(self):
        extensions = cms_config.NavigationCMSExtension()
        config = Mock(
            djangocms_navigation_enabled=True,
            navigation_models=23234,
            app_config=Mock(label="blah_cms_config"),
        )

        with self.assertRaises(ImproperlyConfigured):
            extensions.configure_app(config)

    def test_valid_cms_config_parameter(self):
        extensions = cms_config.NavigationCMSExtension()
        config = Mock(
            djangocms_navigation_enabled=True,
            navigation_models={
                TestModel1: [],
                TestModel2: [],
                TestModel3: [],
                TestModel4: [],
            },
            app_config=Mock(label="blah_cms_config"),
        )

        with self.assertNotRaises(ImproperlyConfigured):
            extensions.configure_app(config)
            register_model = []
            for model in extensions.navigation_apps_models.keys():
                register_model.append(model)

            self.assertTrue(TestModel1 in register_model)
            self.assertTrue(TestModel2 in register_model)
            self.assertTrue(TestModel3 in register_model)
            self.assertTrue(TestModel4 in register_model)


class NavigationIntegrationTestCase(TestCase):
    def setUp(self):
        app_registration.get_cms_extension_apps.cache_clear()
        app_registration.get_cms_config_apps.cache_clear()

    def tearDown(self):
        app_registration.get_cms_extension_apps.cache_clear()
        app_registration.get_cms_config_apps.cache_clear()

    def test_config_with_multiple_apps(self):
        setup_cms_apps()
        registered_models = supported_models()

        expected_models = {
            TestModel1: [],
            TestModel2: [],
            TestModel3: [],
            TestModel4: [],
            Page: ["title"],
            PollContent: ["text"],
        }
        self.assertDictEqual(registered_models, expected_models)


class NavigationSettingTestCase(TestCase):
    def setUp(self):
        self.app = apps.get_app_config('djangocms_navigation')
        # Empty the list of registered models so it gets populated
        # from scratch in tests
        self.app.cms_extension.navigation_apps_models = {}

    def tearDown(self):
        # Populate everything again so our setting changes do not effect
        # any other tests
        imp.reload(cms_config)
        self.app.cms_extension.navigation_apps_models = {}
        self.app.cms_config = cms_config.NavigationCMSAppConfig(self.app)
        configure_cms_apps([self.app])

    def test_cms_models_added_to_navigation_by_default(self):
        imp.reload(cms_config)  # Reload so setting gets checked again
        # The app should have a cms config with the overridden setting
        self.app.cms_config = cms_config.NavigationCMSAppConfig(self.app)

        configure_cms_apps([self.app])

        self.assertIn(Page, self.app.cms_extension.navigation_apps_models)

    @override_settings(DJANGOCMS_NAVIGATION_CMS_MODELS_ENABLED=True)
    def test_cms_models_added_to_navigation_if_enabled(self):
        imp.reload(cms_config)  # Reload so setting gets checked again
        # The app should have a cms config with the overridden setting
        self.app.cms_config = cms_config.NavigationCMSAppConfig(self.app)

        configure_cms_apps([self.app])

        self.assertIn(Page, self.app.cms_extension.navigation_apps_models)

    @override_settings(DJANGOCMS_NAVIGATION_CMS_MODELS_ENABLED=False)
    def test_cms_models_not_added_to_navigation_if_disabled(self):
        imp.reload(cms_config)  # Reload so setting gets checked again
        # The app should have a cms config with the overridden setting
        self.app.cms_config = cms_config.NavigationCMSAppConfig(self.app)

        configure_cms_apps([self.app])

        self.assertNotIn(Page, self.app.cms_extension.navigation_apps_models)


class VersioningSettingTestCase(TestCase):
    def setUp(self):
        self.versioning_app = apps.get_app_config('djangocms_versioning')
        # Empty the list of registered models so it gets populated
        # from scratch in tests
        self.versioning_app.cms_extension.versionables = []

    def tearDown(self):
        """Populate everything again so our setting changes do not
        effect any other tests"""
        # Set the defaults for the navigation app config again
        imp.reload(cms_config)
        navigation_app = apps.get_app_config('djangocms_navigation')
        navigation_app.cms_config = cms_config.NavigationCMSAppConfig(navigation_app)
        # Reset the versioning app
        self.versioning_app.cms_extension.versionables = []
        configure_cms_apps([self.versioning_app])

    def test_navigation_is_versioned_by_default(self):
        imp.reload(cms_config)  # Reload so setting gets checked again
        # The app should have a cms config with the overridden setting
        navigation_app = apps.get_app_config('djangocms_navigation')
        navigation_app.cms_config = cms_config.NavigationCMSAppConfig(navigation_app)

        with patch.object(app_registration, 'get_cms_config_apps', return_value=[navigation_app]):
            configure_cms_apps([self.versioning_app])

        self.assertEqual(len(self.versioning_app.cms_extension.versionables), 1)
        self.assertEqual(self.versioning_app.cms_extension.versionables[0].content_model, MenuContent)

    @override_settings(DJANGOCMS_NAVIGATION_VERSIONING_ENABLED=True)
    def test_navigation_is_versioned_if_versioning_setting_enabled(self):
        imp.reload(cms_config)  # Reload so setting gets checked again
        # The app should have a cms config with the overridden setting
        navigation_app = apps.get_app_config('djangocms_navigation')
        navigation_app.cms_config = cms_config.NavigationCMSAppConfig(navigation_app)

        with patch.object(app_registration, 'get_cms_config_apps', return_value=[navigation_app]):
            configure_cms_apps([self.versioning_app])

        self.assertEqual(len(self.versioning_app.cms_extension.versionables), 1)
        self.assertEqual(self.versioning_app.cms_extension.versionables[0].content_model, MenuContent)

    @override_settings(DJANGOCMS_NAVIGATION_VERSIONING_ENABLED=False)
    def test_navigation_is_versioned_if_versioning_setting_disabled(self):
        imp.reload(cms_config)  # Reload so setting gets checked again
        # The app should have a cms config with the overridden setting
        navigation_app = apps.get_app_config('djangocms_navigation')
        navigation_app.cms_config = cms_config.NavigationCMSAppConfig(navigation_app)

        with patch.object(app_registration, 'get_cms_config_apps', return_value=[navigation_app]):
            configure_cms_apps([self.versioning_app])

        self.assertEqual(len(self.versioning_app.cms_extension.versionables), 0)


class VersionLockingSettingTestCase(TestCase):
    def setUp(self):
        self.versionlocking_app = apps.get_app_config('djangocms_version_locking')
        # Empty the list of registered models so it gets populated
        # from scratch in tests
        self.versionlocking_app.cms_extension.version_lock_models = []

    def tearDown(self):
        """Populate everything again so our setting changes do not
        effect any other tests"""
        # Set the defaults for the navigation app config again
        imp.reload(cms_config)
        navigation_app = apps.get_app_config('djangocms_navigation')
        navigation_app.cms_config = cms_config.NavigationCMSAppConfig(navigation_app)
        # Reset the versioning app
        self.versionlocking_app.cms_extension.version_lock_models = []
        configure_cms_apps([self.versionlocking_app])

    @override_settings(VERSION_LOCKING_CMS_MODELS_ENABLED=True)
    def test_navigation_is_versionlocked_if_versionlock_setting_enabled(self):
        imp.reload(cms_config)  # Reload so setting gets checked again
        # The app should have a cms config with the overridden setting
        navigation_app = apps.get_app_config('djangocms_navigation')
        navigation_app.cms_config = cms_config.NavigationCMSAppConfig(navigation_app)

        with patch.object(app_registration, 'get_cms_config_apps', return_value=[navigation_app]):
            with patch.object(self.versionlocking_app.cms_extension, 'configure_app') as mocked_configure_app:
                configure_cms_apps([self.versionlocking_app])

        self.assertEqual(mocked_configure_app.call_count, 1)


    @override_settings(VERSION_LOCKING_CMS_MODELS_ENABLED=False)
    def test_navigation_is_versionlocked_if_versionlock_setting_disabled(self):
        imp.reload(cms_config)  # Reload so setting gets checked again
        # The app should have a cms config with the overridden setting
        navigation_app = apps.get_app_config('djangocms_navigation')
        navigation_app.cms_config = cms_config.NavigationCMSAppConfig(navigation_app)


        with patch.object(app_registration, 'get_cms_config_apps', return_value=[navigation_app]):
            with patch.object(self.versionlocking_app.cms_extension, 'configure_app') as mocked_configure_app:
                configure_cms_apps([self.versionlocking_app])

        self.assertEqual(mocked_configure_app.call_count, 0)
