from django.contrib.contenttypes.models import ContentType

from cms.models import User

from .base import BaseViewTestCase


class ContentObjectAutoFillTestCases(BaseViewTestCase):
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
        with self.login_user_context(self.user_with_no_perm):
            response = self.client.get(self.select2_endpoint)
            expected_url = "/en/admin/login/?next=" + self.select2_endpoint
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, expected_url)

    def test_return_poll_content_in_select2_view(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={
                    "content_type_id": self.poll_content_contenttype_id,
                    "query": "example",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [p["id"] for p in response.json()["results"]], [self.poll_content.pk]
        )

    def test_return_empty_list_for_query_that_doesnt_match_poll_content_in_select2_view(
        self
    ):
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={
                    "content_type_id": self.poll_content_contenttype_id,
                    "query": "test",
                },
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
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={"content_type_id": self.page_contenttype_id},
            )
        self.assertEqual(response.status_code, 200)
        expected_list = [{"text": "test", "id": 1}, {"text": "test2", "id": 2}]
        self.assertEqual(response.json()["results"], expected_list)

    def test_select2_view_search_text_page(self):
        """ Both pages should appear in results for test query"""
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={"content_type_id": self.page_contenttype_id, "query": "test"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 2)

    def test_select2_view_search_exact_text_page(self):
        """ One page should appear in results for test2 exact query"""
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={"content_type_id": self.page_contenttype_id, "query": "test2"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        # our query should be in text of resultset
        self.assertIn("test2", response.json()["results"][0]["text"])

    def test_select2_view_dummy_search_text_page(self):
        """ query which doesnt match should return 0 results"""
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={"content_type_id": self.page_contenttype_id, "query": "dummy"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 0)

    def test_select2_view_text_poll_content_repr(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={"content_type_id": self.poll_content_contenttype_id},
            )
        self.assertEqual(response.status_code, 200)
        expected_json = {
            "results": [{"text": "example", "id": 1}, {"text": "example2", "id": 2}]
        }
        self.assertEqual(response.json(), expected_json)

    def test_select2_poll_content_view_pk(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.select2_endpoint,
                data={
                    "content_type_id": self.poll_content_contenttype_id,
                    "site": self.site2.pk,
                    "pk": self.poll_content.pk,
                },
            )
        self.assertEqual(response.status_code, 200)
        expected_result_list = [{"text": "example", "id": 1}]
        self.assertListEqual(response.json()["results"], expected_result_list)
