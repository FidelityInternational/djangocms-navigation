from unittest.mock import Mock, patch

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from cms.models import Page, User
from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.utils import get_object_edit_url, get_object_preview_url

from djangocms_versioning.constants import (
    ARCHIVED,
    DRAFT,
    PUBLISHED,
    UNPUBLISHED,
)

from djangocms_navigation.models import MenuContent
from djangocms_navigation.test_utils import factories
from djangocms_navigation.test_utils.app_1.models import TestModel1, TestModel2
from djangocms_navigation.test_utils.app_2.models import TestModel3, TestModel4
from djangocms_navigation.test_utils.polls.models import PollContent
from djangocms_navigation.utils import (
    get_latest_page_content_for_page_grouper,
    is_model_supported,
    is_preview_or_edit_mode,
    supported_content_type_pks,
    supported_models,
)


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
            self.assertEqual(supported_models(MenuContent), models)

    @patch.object(apps, "get_app_config", side_effect=LookupError)
    def test_supported_models_returns_empty_list_on_lookup_error(self, mocked_apps):
        self.assertDictEqual(supported_models(MenuContent), {})

    def test_supported_models_is_cached(self):
        models = ["Foo", "Bar"]
        app_config = Mock(
            spec=[], cms_extension=Mock(spec=[], navigation_apps_models=models)
        )
        with patch.object(apps, "get_app_config", return_value=app_config):
            supported_models(MenuContent)
        with patch.object(apps, "get_app_config") as mock:
            supported_models(MenuContent)
            mock.assert_not_called()


class SupportedContentTypePksTestCase(TestCase):
    def setUp(self):
        supported_content_type_pks.cache_clear()

    def tearDown(self):
        supported_content_type_pks.cache_clear()

    def test_supported_content_types(self):
        expected_content_types = ContentType.objects.get_for_models(
            Page, TestModel1, TestModel2, TestModel3, TestModel4, PollContent
        )
        expected_pks = [ct.pk for ct in expected_content_types.values()]
        self.assertSetEqual(set(supported_content_type_pks(MenuContent)), set(expected_pks))

    def test_supported_content_types_is_cached(self):
        self.assertTrue(hasattr(supported_content_type_pks, "cache_info"))


class IsModelSupportedTestCase(TestCase):
    def setUp(self):
        supported_content_type_pks.cache_clear()

    def tearDown(self):
        supported_content_type_pks.cache_clear()

    def test_supported_content_types(self):
        expected_content_types = ContentType.objects.get_for_models(
            Page, TestModel1, TestModel2, TestModel3, TestModel4, PollContent
        )
        for model in expected_content_types:
            self.assertTrue(is_model_supported(MenuContent, model))

    def test_non_supported_content_types(self):
        unexpected_content_types = ContentType.objects.get_for_models(User)
        for model in unexpected_content_types:
            self.assertFalse(is_model_supported(MenuContent, model))


class CMSMenuTestCase(CMSTestCase):
    """
    Test case for the utility: is_preview_or_edit_mode
    """
    def setUp(self):
        self.page_content = factories.PageContentWithVersionFactory(
            version__created_by=self.get_superuser(),
            version__state=PUBLISHED,
        )

    def test_live_endpoint(self):
        live_endpoint = self.page_content.get_absolute_url(language=self.page_content.language)

        response = self.client.get(live_endpoint)
        actual = is_preview_or_edit_mode(response.wsgi_request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(actual)

    def test_preview_endpoint(self):
        preview_endpoint = get_object_preview_url(self.page_content, language=self.page_content.language)

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(preview_endpoint)
        actual = is_preview_or_edit_mode(response.wsgi_request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(actual)

    def test_edit_endpoint(self):
        edit_endpoint = get_object_edit_url(self.page_content, language=self.page_content.language)

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(edit_endpoint)
        actual = is_preview_or_edit_mode(response.wsgi_request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(actual)


class PreviewEditModeTestCase(TestCase):
    """
    Test case for the utility: get_latest_page_content_for_page_grouper
    """
    def test_draft_page_is_returned(self):
        page_content = factories.PageContentWithVersionFactory(
            version__state=DRAFT,
        )
        actual = get_latest_page_content_for_page_grouper(page_content.page, page_content.language)

        self.assertEqual(page_content, actual)
        self.assertIsNotNone(actual)

    def test_published_page_is_returned(self):
        page_content = factories.PageContentWithVersionFactory(
            version__state=PUBLISHED,
        )
        actual = get_latest_page_content_for_page_grouper(page_content.page, page_content.language)

        self.assertEqual(page_content, actual)
        self.assertIsNotNone(actual)

    def test_archived_page_is_not_returned(self):
        page_content = factories.PageContentWithVersionFactory(
            version__state=ARCHIVED,
        )
        actual = get_latest_page_content_for_page_grouper(page_content.page, page_content.language)

        self.assertNotEqual(page_content, actual)
        self.assertIsNone(actual)

    def test_unpublished_page_is_not_returned(self):
        page_content = factories.PageContentWithVersionFactory(
            version__state=UNPUBLISHED,
        )
        actual = get_latest_page_content_for_page_grouper(page_content.page, page_content.language)

        self.assertNotEqual(page_content, actual)
        self.assertIsNone(actual)
