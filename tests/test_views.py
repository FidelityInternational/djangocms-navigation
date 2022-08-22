from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

from cms.models import Page, User
from cms.test_utils.testcases import CMSTestCase
from cms.utils.urlutils import admin_reverse

from djangocms_navigation.constants import SELECT2_CONTENT_OBJECT_URL_NAME
from djangocms_navigation.test_utils.factories import (
    MenuContentFactory,
    PageContentFactory,
)
from djangocms_navigation.test_utils.polls.models import Poll, PollContent


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
