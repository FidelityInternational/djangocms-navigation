from unittest.mock import Mock, patch

from django.apps import apps

from cms.test_utils.testcases import CMSTestCase

from djangocms_navigation.utils import supported_models


class UtilsTestCase(CMSTestCase):

    def setUp(self):
        supported_models.cache_clear()

    def tearDown(self):
        supported_models.cache_clear()

    def test_supported_models(self):
        models = ['Foo', 'Bar']
        app_config = Mock(spec=[], cms_extension=Mock(spec=[], navigation_apps_models=models))
        with patch.object(apps, 'get_app_config', return_value=app_config):
            self.assertEqual(
                supported_models(),
                models,
            )

    @patch.object(apps, 'get_app_config', side_effect=LookupError)
    def test_supported_models_returns_empty_list_on_lookup_error(self, mocked_apps):
        self.assertListEqual(supported_models(), [])

    def test_supported_models_is_cached(self):
        models = ['Foo', 'Bar']
        app_config = Mock(spec=[], cms_extension=Mock(spec=[], navigation_apps_models=models))
        with patch.object(apps, 'get_app_config', return_value=app_config):
            supported_models()
        with patch.object(apps, 'get_app_config') as mock:
            supported_models()
            mock.assert_not_called()
