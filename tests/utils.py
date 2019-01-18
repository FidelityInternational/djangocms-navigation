import unittest
from contextlib import contextmanager

from django.contrib import messages


class UsefulAssertsMixin(object):
    def assertRedirectsToVersionList(self, response, version):
        """Asserts the response redirects to the menu content version list"""
        version_list_url = self.get_admin_url(
            version.versionable.version_model_proxy, 'changelist')
        version_list_url += '?menu=' + str(version.content.menu.id)
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
