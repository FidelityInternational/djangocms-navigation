from unittest.mock import Mock, patch

from django.apps import apps

from cms.test_utils.testcases import CMSTestCase

from djangocms_navigation.utils import supported_models


class UtilsTestCase(CMSTestCase):

    def test_supported_models(self):
        models = ['Foo', 'Bar']
        app_config = Mock(spec=[], cms_extension=Mock(spec=[], navigation_apps_models=models))
        with patch.object(apps, 'get_app_config', return_value=app_config):
            self.assertEqual(
                supported_models(),
                models,
            )

    def test_supported_models_is_cached(self):
        models = ['Foo', 'Bar']
        app_config = Mock(spec=[], cms_extension=Mock(spec=[], navigation_apps_models=models))
        with patch.object(apps, 'get_app_config', return_value=app_config):
            supported_models()
        with patch.object(apps, 'get_app_config') as mock:
            supported_models()
            mock.assert_not_called()
