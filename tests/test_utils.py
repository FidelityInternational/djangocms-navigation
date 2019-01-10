from unittest.mock import Mock, patch

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from cms.models import Page

from djangocms_navigation.test_utils.app_1.models import TestModel1, TestModel2
from djangocms_navigation.test_utils.app_2.models import TestModel3, TestModel4
from djangocms_navigation.utils import supported_content_type_pks, supported_models


class SupportedModelsTestCase(TestCase):
    def setUp(self):
        supported_models.cache_clear()

    def tearDown(self):
        supported_models.cache_clear()

    def test_supported_models(self):
        models = ["Foo", "Bar"]
        app_config = Mock(
            spec=[], cms_extension=Mock(spec=[], navigation_apps_models=models)
        )
        with patch.object(apps, "get_app_config", return_value=app_config):
            self.assertEqual(supported_models(), models)

    @patch.object(apps, "get_app_config", side_effect=LookupError)
    def test_supported_models_returns_empty_list_on_lookup_error(self, mocked_apps):
        self.assertListEqual(supported_models(), [])

    def test_supported_models_is_cached(self):
        models = ["Foo", "Bar"]
        app_config = Mock(
            spec=[], cms_extension=Mock(spec=[], navigation_apps_models=models)
        )
        with patch.object(apps, "get_app_config", return_value=app_config):
            supported_models()
        with patch.object(apps, "get_app_config") as mock:
            supported_models()
            mock.assert_not_called()


class SupportedContentTypePksTestCase(TestCase):
    def setUp(self):
        supported_content_type_pks.cache_clear()

    def tearDown(self):
        supported_content_type_pks.cache_clear()

    def test_supported_content_types(self):
        expected_content_types = ContentType.objects.get_for_models(
            Page, TestModel1, TestModel2, TestModel3, TestModel4)
        expected_pks = [ct.pk for ct in expected_content_types.values()]
        self.assertSetEqual(
            set(supported_content_type_pks()), set(expected_pks))

    def test_supported_content_types_is_cached(self):
        self.assertTrue(hasattr(supported_content_type_pks, 'cache_info'))
