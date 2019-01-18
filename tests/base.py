from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

from cms.models import Page
from cms.test_utils.testcases import CMSTestCase
from cms.utils.urlutils import admin_reverse

from djangocms_navigation.constants import SELECT2_CONTENT_OBJECT_URL_NAME
from djangocms_navigation.test_utils.factories import PageContentFactory
from djangocms_navigation.test_utils.polls.models import Poll, PollContent


class BaseViewTestCase(CMSTestCase):
    """setup data  for view test case"""

    select2_endpoint = admin_reverse(SELECT2_CONTENT_OBJECT_URL_NAME)

    def setUp(self):
        self.language = "en"
        self.superuser = self.get_superuser()
        self.user_with_no_perm = self.get_standard_user()
        self.page = PageContentFactory(
            title="test", menu_title="test", page_title="test", language=self.language
        )
        self.default_site = Site.objects.first()
        self.site2 = Site.objects.create(name="foo.com", domain="foo.com")
        self.page2 = PageContentFactory(
            title="test2",
            menu_title="test2",
            page_title="test2",
            language=self.language,
        )

        self.poll = Poll.objects.create(name="Test poll")
        self.poll_content = PollContent.objects.create(
            poll=self.poll, language=self.language, text="example"
        )
        self.poll_content2 = PollContent.objects.create(
            poll=self.poll, language=self.language, text="example2"
        )
        self.page_contenttype_id = ContentType.objects.get_for_model(Page).id
        self.poll_content_contenttype_id = ContentType.objects.get_for_model(
            PollContent
        ).id

    @classmethod
    def is_versioning_enabled(cls):
        return "djangocms_versioning" in settings.INSTALLED_APPS

    def _get_version(self, grouper, version_state, language=None):
        language = language or self.language

        from djangocms_versioning.models import Version

        version = (
            Version.objects.filter_by_grouper(grouper)
            .filter(state=version_state)
            .order_by("id")
            .last()
        )
        return version
