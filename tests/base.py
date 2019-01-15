from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

from cms.api import create_page
from cms.models import Page
from cms.test_utils.testcases import CMSTestCase
from cms.utils.urlutils import admin_reverse

from djangocms_navigation.constants import SELECT2_CONTENT_OBJECT_URL_NAME
from djangocms_navigation.test_utils.polls.models import Poll, PollContent


class BaseUrlTestCase(CMSTestCase):
    select2_endpoint = admin_reverse(SELECT2_CONTENT_OBJECT_URL_NAME)

    def setUp(self):
        self.language = "en"
        self.superuser = self.get_superuser()
        self.page = self._create_page(title="test", language=self.language)
        self.placeholder = self.page.get_placeholders(self.language).get(slot="content")
        self.default_site = Site.objects.first()
        self.site2 = Site.objects.create(name="foo.com", domain="foo.com")
        self.page2 = self._create_page(
            title="test2", language=self.language, site=self.site2
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

        versions = Version.objects.filter_by_grouper(grouper).filter(
            state=version_state
        )
        for version in versions:
            if (
                hasattr(version.content, "language")
                and version.content.language == language
            ):
                return version

    def _publish(self, grouper, language=None):
        from djangocms_versioning.constants import DRAFT

        version = self._get_version(grouper, DRAFT, language)
        version.publish(self.superuser)

    def _create_page(self, title, language=None, site=None, published=True, **kwargs):
        if language is None:
            language = self.language

        if self.is_versioning_enabled() and not kwargs.get("created_by"):
            kwargs["created_by"] = self.superuser

        page = create_page(
            title=title,
            language=language,
            template="page.html",
            menu_title="",
            in_navigation=True,
            limit_visibility_in_menu=None,
            site=site,
            **kwargs
        )

        if self.is_versioning_enabled() and published:
            self._publish(page, language)

        return page
