import unittest
from contextlib import contextmanager

from django.apps import apps
from django.contrib import messages

from djangocms_navigation.models import MenuContent
from djangocms_versioning.helpers import version_list_url_for_grouper


class UsefulAssertsMixin(object):
    def assertRedirectsToVersionList(self, response, menu):
        """Asserts the response redirects to the menu content version list"""
        version_list_url = version_list_url_for_grouper(menu)
        self.assertRedirects(response, version_list_url)

    def assertDjangoErrorMessage(self, msg, mocked_messages):
        """Mock 'django.contrib.messages.add_message' to use this assert
        method and pass the mocked object as mocked_messages."""
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], msg)


class TestCase(unittest.TestCase):
    @contextmanager
    def assertNotRaises(self, exc_type):
        try:
            yield None
        except exc_type:
            raise self.failureException("{} raised".format(exc_type.__name__))


class VersioningHelpersMixin(object):
    @contextmanager
    def disable_versioning(self):
        """Use with the with statement to disable versioning of MenuContent.
        This does NOT set the NAVIGATION_VERSIONING_ENABLED setting to False
        or change djangocms_versioning_enabled in cms_config to False.
        You will have to do that manually on your test"""
        self.versioning_ext = apps.get_app_config('djangocms_versioning').cms_extension
        self.menu_versionable = self.versioning_ext.versionables_by_content[MenuContent]
        self.versioning_ext.versionables.remove(self.menu_versionable)
        del self.versioning_ext.versionables_by_content
        #~ del self.versioning_ext.versionables_by_grouper
        try:
            yield None
        finally:
            self.versioning_ext.versionables.append(self.menu_versionable)
            del self.versioning_ext.versionables_by_content
            #~ del self.versioning_ext.versionables_by_grouper
