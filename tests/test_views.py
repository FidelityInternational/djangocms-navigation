from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.test import override_settings

from cms.models import Page, PageContent, User
from cms.test_utils.testcases import CMSTestCase
from cms.utils import get_current_site
from cms.utils.urlutils import admin_reverse

from djangocms_versioning.constants import PUBLISHED
from faker import Faker

from djangocms_navigation.constants import SELECT2_CONTENT_OBJECT_URL_NAME
from djangocms_navigation.models import MenuContent
from djangocms_navigation.test_utils.factories import (
    MenuContentFactory,
    PageContentFactory,
    PageContentWithVersionFactory,
)
from djangocms_navigation.test_utils.polls.models import Poll, PollContent
from djangocms_navigation.views import ContentObjectSelect2View


fake = Faker()


class PreviewViewPermissionTestCases(CMSTestCase):
    def setUp(self):
        self.menu_content = MenuContentFactory()
        self.preview_url = admin_reverse(
            "djangocms_navigation_menuitem_preview",
            kwargs={"menu_content_id": self.menu_content.id},
        )

    def test_anonymous_user_cannot_access_preview(self):
        response = self.client.get(self.preview_url)
        expected_url = "/en/admin/login/?next=" + self.preview_url
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_url)

    def test_standard_user_cannot_access_preview(self):
        with self.login_user_context(self.get_standard_user()):
            response = self.client.get(self.preview_url)
            expected_url = "/en/admin/login/?next=" + self.preview_url
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, expected_url)


class ContentObjectAutoFillTestCases(CMSTestCase):
    def setUp(self):
        self.select2_endpoint = admin_reverse(SELECT2_CONTENT_OBJECT_URL_NAME)
        self.superuser = self.get_superuser()

    def test_select2_view_no_content_id(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(self.select2_endpoint)
            self.assertEqual(response.status_code, 400)

    def test_select2_view_anonymous_user(self):
        """HTTP get shouldn't allowed for anonymous user"""
        response = self.client.get(self.select2_endpoint)
        expected_url = "/en/admin/login/?next=" + self.select2_endpoint
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_url)

    def test_select2_view_endpoint_post(self):
        """HTTP post shouldn't allowed on this endpoint"""
        response = self.client.post(self.select2_endpoint)
        expected_url = "/en/admin/login/?next=" + self.select2_endpoint
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_url)

    def test_select2_view_endpoint_user_with_no_perm(self):
        """HTTP get shouldn't allowed for standard non staff user"""
        user_with_no_perm = self.get_standard_user()

        with self.login_user_context(user_with_no_perm):
            response = self.client.get(self.select2_endpoint)
            expected_url = "/en/admin/login/?next=" + self.select2_endpoint
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, expected_url)

    def test_return_poll_content_in_select2_view(self):
        poll_content_contenttype_id = ContentType.objects.get_for_model(PollContent).id
        poll = Poll.objects.create(name="Test poll")

        poll_content = PollContent.objects.create(
            poll=poll, language="en", text="example"
        )

        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={
                    "content_type_id": poll_content_contenttype_id,
                    "query": "example",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [p["id"] for p in response.json()["results"]], [poll_content.pk]
        )

    def test_return_empty_list_for_query_that_doesnt_match_poll_content_in_select2_view(
        self
    ):
        poll_content_contenttype_id = ContentType.objects.get_for_model(PollContent).id
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={"content_type_id": poll_content_contenttype_id, "query": "test"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([p["id"] for p in response.json()["results"]], [])

    def test_raise_error_when_return_unregistered_user_model_in_select2_view(self):
        """view should raise bad http request for non registered model"""
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={"content_type_id": ContentType.objects.get_for_model(User).id},
            )
            self.assertEqual(response.status_code, 400)

    def test_select2_view_text_page_repr(self):
        """Result should contain model repr text"""
        page_contenttype_id = ContentType.objects.get_for_model(Page).id
        PageContentFactory(
            title="test", menu_title="test", page_title="test", language="en"
        )  # flake8: noqa
        PageContentFactory(
            title="test2", menu_title="test2", page_title="test2", language="en"
        )  # flake8: noqa
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint, data={"content_type_id": page_contenttype_id}
            )
        self.assertEqual(response.status_code, 200)
        expected_list = [{"text": "test", "id": 1}, {"text": "test2", "id": 2}]
        self.assertEqual(response.json()["results"], expected_list)
        self.assertEqual(len(response.json()["results"]), 2)

    def test_select2_view_search_text_page(self):
        """ Both pages should appear in results for test query"""
        page_contenttype_id = ContentType.objects.get_for_model(Page).id
        PageContentFactory(
            title="test", menu_title="test", page_title="test", language="en"
        )
        PageContentFactory(
            title="test2", menu_title="test2", page_title="test2", language="en"
        )
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={"content_type_id": page_contenttype_id, "query": "test"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 2)

    def test_select2_view_search_exact_text_page(self):
        """ One page should appear in results for test2 exact query"""
        page_contenttype_id = ContentType.objects.get_for_model(Page).id
        PageContentFactory(
            title="test", menu_title="test", page_title="test", language="en"
        )
        PageContentFactory(
            title="test2", menu_title="test2", page_title="test2", language="en"
        )
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={"content_type_id": page_contenttype_id, "query": "test2"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        # our query should be in text of resultset
        self.assertIn("test2", response.json()["results"][0]["text"])

    def test_select2_view_dummy_search_text_page(self):
        """ query which doesnt match should return 0 results"""
        page_contenttype_id = ContentType.objects.get_for_model(Page).id
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={"content_type_id": page_contenttype_id, "query": "dummy"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 0)

    def test_select2_view_text_poll_content_repr(self):
        poll_content_contenttype_id = ContentType.objects.get_for_model(PollContent).id

        poll = Poll.objects.create(name="Test poll")
        PollContent.objects.create(poll=poll, language="en", text="example1")
        PollContent.objects.create(poll=poll, language="en", text="example2")

        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={"content_type_id": poll_content_contenttype_id},
            )
        self.assertEqual(response.status_code, 200)
        expected_json = {
            "results": [{"text": "example1", "id": 1}, {"text": "example2", "id": 2}]
        }
        self.assertEqual(response.json(), expected_json)

    def test_select2_poll_content_view_pk(self):
        site = Site.objects.create(name="foo.com", domain="foo.com")
        poll_content_contenttype_id = ContentType.objects.get_for_model(PollContent).id
        poll = Poll.objects.create(name="Test poll")

        poll_content = PollContent.objects.create(
            poll=poll, language="en", text="example"
        )
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={
                    "content_type_id": poll_content_contenttype_id,
                    "site": site.pk,
                    "pk": poll_content.pk,
                },
            )
        self.assertEqual(response.status_code, 200)
        expected_json = {"results": [{"text": "example", "id": 1}]}
        self.assertEqual(response.json(), expected_json)

    @override_settings(DJANGOCMS_NAVIGATION_VERSIONING_ENABLED=True)
    def test_with_multiple_versions_distinct_results_returned(self):
        """
        Check that when there are multiple Pages, and each have multiple versions of PageContent, that the returned
        Page objects are distinct and do not contain duplicate titles/ids
        """
        page_contenttype_id = ContentType.objects.get_for_model(Page).id
        first_page = PageContentWithVersionFactory(
            title="test", menu_title="test", page_title="test", language="en", version__state=PUBLISHED
        )
        # create a draft version of the page
        first_page_new_version = first_page.versions.get().copy(self.superuser)
        first_page_new_version.save()
        second_page = PageContentWithVersionFactory(
            title="test2", menu_title="test2", page_title="test2", language="en"
        )
        # create a draft version and publish it
        second_page_new_version = second_page.versions.get().copy(self.superuser)
        second_page_new_version.save()
        second_page_new_version.publish(self.superuser)

        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={"content_type_id": page_contenttype_id, "query": "test"},
            )
            results = response.json()["results"]

        self.assertEqual(Page._base_manager.count(), 2)
        self.assertEqual(PageContent._base_manager.count(), 4)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(results), 2)
        expected = [
            {"text": "test", "id": first_page.page.pk},
            {"text": "test2", "id": second_page.page.pk}
        ]
        self.assertEqual(results, expected)

    def test_with_pages_in_multiple_languages(self):
        """
        Check that when page content exists in multiple languages, only pages for the current language are returned
        """
        page_contenttype_id = ContentType.objects.get_for_model(Page).id
        french = PageContentFactory(
            title="test", menu_title="test", page_title="test", language="fr",
        )
        PageContentFactory.create_batch(10, title="test", menu_title="test", page_title="test", language="en")

        with self.login_user_context(self.superuser):
            url = self.select2_endpoint.replace("/en/", "/fr/")
            response = self.client.get(
                url,
                data={"content_type_id": page_contenttype_id, "query": "test"},
            )
            results = response.json()["results"]

        self.assertEqual(PageContent._base_manager.count(), 11)
        self.assertEqual(len(results), 1)
        expected = [
            {"text": "test", "id": french.page.pk},
        ]
        self.assertEqual(results, expected)

    def test_with_pages_for_multiple_sites(self):
        """
        Check that with pages for multiple sites, only pages for the requested site are returned
        """
        page_contenttype_id = ContentType.objects.get_for_model(Page).id
        site1 = Site.objects.create(name="site1.com", domain="site1.com")
        site2 = Site.objects.create(name="site2.com", domain="site2.com")
        PageContentFactory.create_batch(10, title="test", page__node__site=site1, language="en")
        expected = PageContentFactory(title="test", menu_title="site2 page", page__node__site=site2, language="en")

        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={
                    "content_type_id": page_contenttype_id,
                    "site": site2.id
                },
            )
            results = response.json()["results"]

        self.assertEqual(PageContent._base_manager.count(), 11)
        self.assertEqual(len(results), 1)
        self.assertEqual(results, [{"id": expected.page.id, "text": "site2 page"}])

    def test_searching_for_page_slug(self):
        """
        Check that when the search query is a PageUrl path, the correct page is returned
        """
        page_contenttype_id = ContentType.objects.get_for_model(Page).id
        PageContentFactory.create_batch(10, language="en")
        expected = PageContentFactory(title="Test search by slug", menu_title="Test search by slug", language="en")
        slug = expected.page.get_slug("en")
        # early smoke test to stop us getting a false positive by finding the page by its title rather than slug
        self.assertNotEqual(expected.title.lower(), slug)

        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={
                    "content_type_id": page_contenttype_id,
                    "query": slug,
                },
            )
            results = response.json()["results"]

        self.assertEqual(PageContent._base_manager.count(), 11)
        self.assertEqual(len(results), 1)
        self.assertEqual(results, [{"id": expected.page.id, "text": "Test search by slug"}])

    def test_searching_for_page_path(self):
        """
        Check that when the search query is a PageUrl path, the correct page is returned
        """
        page_contenttype_id = ContentType.objects.get_for_model(Page).id
        PageContentFactory.create_batch(10, language="en")
        expected = PageContentFactory(menu_title="Test search by overwritten url", language="en")
        # update page urls to use a randomly generated path to represent setting an overwritten url
        path = fake.uri_path()
        expected.page.urls.update(path=path)
        # early smoke test to stop us getting a false positive by finding the page by its slug rather than path
        self.assertNotEqual(expected.page.get_slug("en"), path)

        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={
                    "content_type_id": page_contenttype_id,
                    "query": path,
                },
            )
            results = response.json()["results"]

        self.assertEqual(PageContent._base_manager.count(), 11)
        self.assertEqual(len(results), 1)
        self.assertEqual(results, [{"id": expected.page.id, "text": "Test search by overwritten url"}])


class ContentObjectSelect2ViewGetDataTestCase(CMSTestCase):
    """
    Unit tests for the get_data method of the ContentObjectSelect2View
    """
    def setUp(self):
        """
        Setup a view object with a request without a search query that can be used in unit tests.
        The request object can be modified as required for the unit test.
        """
        self.page_contenttype_id = ContentType.objects.get_for_model(Page).id
        self.request = self.get_request(language="en")
        self.view = ContentObjectSelect2View(request=self.request, menu_content_model=MenuContent)

    @patch("django.db.models.QuerySet.distinct")
    def test_distinct_not_called_without_search_query_for_poll(self, mock_distinct):
        """
        Mock distinct to assert that it is not called if there is no search query in the request for the poll content
        type
        """
        poll_content_contenttype_id = ContentType.objects.get_for_model(PollContent).id
        self.request.GET = {"content_type_id": poll_content_contenttype_id, "query": None}

        self.view.get_data()

        mock_distinct.assert_not_called()

    @patch("django.db.models.QuerySet.distinct")
    def test_distinct_called_with_search_query_for_page(self, mock_distinct):
        """
        Mock distinct to assert that it is called for the page content type even without a search query, because the
        queryset is filtered by language and site
        """
        self.request.GET = {"content_type_id": self.page_contenttype_id, "query": None}

        self.view.get_data()

        mock_distinct.assert_called_once()

    @patch("django.db.models.QuerySet.distinct")
    def test_distinct_called_with_search_query(self, mock_distinct):
        """
        Mock distinct to assert that it is called if there is a search query in the request
        """
        self.request.GET = {"content_type_id": self.page_contenttype_id, "query": "test query"}

        self.view.get_data()

        mock_distinct.assert_called_once()

    def test_results_unfiltered_without_search_fields(self):
        """
        Check that if no search fields have been declared to filter against, the queryset is returned unfiltered
        """
        poll_content_contenttype_id = ContentType.objects.get_for_model(PollContent).id
        poll = Poll.objects.create(name="Test poll")
        poll1 = PollContent.objects.create(poll=poll, language="en", text="poll1")
        poll2 = PollContent.objects.create(poll=poll, language="en", text="poll2")
        self.request.GET = {"content_type_id": poll_content_contenttype_id, "query": "poll1"}

        with patch("djangocms_navigation.views.supported_models") as mock:
            mock.return_value = {PollContent: []}
            results = self.view.get_data()

        self.assertEqual(results.count(), 2)
        self.assertIn(poll1, results)
        self.assertIn(poll2, results)

    def test_results_filtered_by_search_fields(self):
        """
        Check that if the search fields has been declared to filter against, the queryset is returned filtered
        """
        poll_content_contenttype_id = ContentType.objects.get_for_model(PollContent).id
        poll = Poll.objects.create(name="Test poll")
        poll1 = PollContent.objects.create(poll=poll, language="en", text="poll1")
        poll2 = PollContent.objects.create(poll=poll, language="en", text="poll2")
        self.request.GET = {"content_type_id": poll_content_contenttype_id, "query": "poll1"}

        with patch("djangocms_navigation.views.supported_models") as mock:
            mock.return_value = {PollContent: ["text"]}
            results = self.view.get_data()

        self.assertEqual(results.count(), 1)
        self.assertIn(poll1, results)
        self.assertNotIn(poll2, results)

    def test_page_queryset_is_filtered_by_content_title(self):
        """
        Check that the returned Page QuerySet is filtered by the PageContent title
        """
        expected = PageContentFactory(title="Example PageContent", language="en")
        PageContentFactory.create_batch(10)
        self.request.GET = {"content_type_id": self.page_contenttype_id, "query": expected.title}

        results = self.view.get_data()

        self.assertEqual(Page._base_manager.count(), 11)
        self.assertEqual(results.count(), 1)
        self.assertIn(expected.page, results)

    def test_page_queryset_filters_pages_by_current_language(self):
        """
        Check that only the page for the language of the request is returned
        """
        self.en = PageContentFactory(title="english test", language="en")
        self.fr = PageContentFactory(title="french test", language="fr")
        self.de = PageContentFactory(title="german test", language="de")
        self.it = PageContentFactory(title="italian test", language="it")

        for language in ["en", "fr", "de", "it"]:
            with self.subTest(msg=language):
                request = self.get_request(language=language)
                request.GET = {"content_type_id": self.page_contenttype_id, "query": "test"}
                self.view.request = request
                results = self.view.get_data()

                expected = getattr(self, language)
                self.assertEqual(Page._base_manager.count(), 4)
                self.assertEqual(results.count(), 1)
                self.assertIn(expected.page, results)

    @patch("djangocms_navigation.views.get_current_site")
    def test_page_queryset_filtered_by_site(self, mock_get_current_site):
        """
        Check that when pages belong to different sites, the returned queryset only includes pages for the current site
        """
        site1 = Site.objects.create(domain="site1.com", name="site1")
        site2 = Site.objects.create(domain="site2.com", name="site2")
        PageContentFactory.create_batch(10, language="en", page__node__site=site1)
        PageContentFactory.create_batch(10, language="en", page__node__site=site2)

        for site in [site1, site2]:
            with self.subTest(msg=site.name):
                self.request.GET = {"content_type_id": self.page_contenttype_id}
                mock_get_current_site.return_value = site
                results = self.view.get_data()

                expected_domain = results.values_list("node__site__domain", flat=True).distinct()
                self.assertEqual(Page._base_manager.count(), 20)
                self.assertEqual(results.count(), 10)
                self.assertEqual(expected_domain.first(), site.domain)

    def test_when_no_site_param_get_current_site_called(self):
        """
        Check that when no site param is included in the request, that the get_current_site method is called
        """
        self.request.GET = {"content_type_id": self.page_contenttype_id, "site": None}

        # use wraps to allow us to assert the method is called while retaining the original behaviour of the method
        with patch("djangocms_navigation.views.get_current_site", wraps=get_current_site) as mock_get_current_site:
            self.view.get_data()

        mock_get_current_site.assert_called_once()

    def test_page_queryset_is_filtered_by_url_slug(self):
        """
        Check that the returned Page QuerySet is filtered by the PageUrl slug
        """
        # create a batch of Page objects with PageContent
        PageContentFactory.create_batch(100, language="en")
        # get a random page
        expected = Page.objects.order_by("?").first()
        # overwrite page urls slug to a randomly generated slug
        slug = fake.slug()
        expected.urls.update(slug=slug)
        # use the slug to search for the expected page
        self.request.GET = {"content_type_id": self.page_contenttype_id, "query": slug}

        results = self.view.get_data()

        self.assertEqual(Page._base_manager.count(), 100)
        self.assertEqual(results.count(), 1)
        self.assertIn(expected, results)

    def test_page_queryset_is_filtered_by_url_path(self):
        """
        Check that the returned Page QuerySet is filtered by the PageUrl path
        """
        # create a batch of Page objects with PageContent
        PageContentFactory.create_batch(100, language="en")
        # get a random page
        expected = Page.objects.order_by("?").first()
        # overwrite page urls path to a randomly generated path
        path = fake.uri_path()
        expected.urls.update(path=path)
        # use the path to search for the expected page
        self.request.GET = {"content_type_id": self.page_contenttype_id, "query": path}

        results = self.view.get_data()

        self.assertNotEqual(expected.get_slug("en"), path)
        self.assertEqual(Page._base_manager.count(), 100)
        self.assertEqual(results.count(), 1)
        self.assertIn(expected, results)
