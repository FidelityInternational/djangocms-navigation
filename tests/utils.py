from contextlib import contextmanager

from django.apps import apps
from django.conf import UserSettingsHolder, settings
from django.test import RequestFactory
from django.test.signals import setting_changed
from django.test.utils import TestContextDecorator

from cms.toolbar.toolbar import CMSToolbar
from cms.middleware.toolbar import ToolbarMiddleware

from djangocms_versioning.helpers import version_list_url

from djangocms_navigation.cms_toolbars import NavigationToolbar
from djangocms_navigation.test_utils import factories


class UsefulAssertsMixin(object):
    def assertRedirectsToVersionList(self, response, menu_content):
        """Asserts the response redirects to the menu content version list"""
        endpoint = version_list_url(menu_content)
        self.assertRedirects(response, endpoint)

    def assertDjangoErrorMessage(self, msg, mocked_messages):
        """Mock 'django.contrib.messages.error' to use this assert
        method and pass the mocked object as mocked_messages."""
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], msg)

    @contextmanager
    def assertNotRaises(self, exc_type):
        try:
            yield None
        except exc_type:
            raise self.failureException("{} raised".format(exc_type.__name__))


class disable_versioning_for(TestContextDecorator):
    """
    Use this to remove content models from versioning for specific tests.
    For example: `@disable_versioning_for(MenuContent, PageContent)`
    NOTE: This does not change any settings, enabled attributes etc.
    You will need to do this separately if needed for your test.

    Acts as either a decorator or a context manager. If it's a decorator it
    takes a function and returns a wrapped function. If it's a contextmanager
    it's used with the ``with`` statement.
    """
    def __init__(self, *args):
        self.content_models = args
        super(disable_versioning_for, self).__init__()

    def enable(self):
        # Remove the versionables
        self.versioning_ext = apps.get_app_config('djangocms_versioning').cms_extension
        self.versionables_to_remove = [
            self.versioning_ext.versionables_by_content[model]
            for model in self.content_models
        ]
        for versionable in self.versionables_to_remove:
            self.versioning_ext.versionables.remove(versionable)
        # Reset versioning's cached properties
        if hasattr(self.versioning_ext, 'versionables_by_content'):
            del self.versioning_ext.versionables_by_content
        if hasattr(self.versioning_ext, 'versionables_by_grouper'):
            del self.versioning_ext.versionables_by_grouper

    def disable(self):
        # Re-add the versionables
        self.versioning_ext.versionables.extend(self.versionables_to_remove)
        # Reset versioning's cached properties
        if hasattr(self.versioning_ext, 'versionables_by_content'):
            del self.versioning_ext.versionables_by_content
        if hasattr(self.versioning_ext, 'versionables_by_grouper'):
            del self.versioning_ext.versionables_by_grouper


class disable_versioning_for_navigation(disable_versioning_for):
    """
    Like disable_versioning_for, but specifically removes the navigation
    models from versionables and additionally sets
    settings.NAVIGATION_VERSIONING_ENABLED and djangocms_versioning_enabled
    on the navigation config to False.
    """
    def __init__(self):
        self.navigation_config = apps.get_app_config(
            'djangocms_navigation').cms_config
        nav_content_models = [
            v.content_model
            for v in self.navigation_config.versioning
        ]
        super().__init__(*nav_content_models)

    def enable(self):
        # Save previous value of djangocms_versioning_enabled and then set to False
        self._prev_versioning_enabled = self.navigation_config.djangocms_versioning_enabled
        self.navigation_config.djangocms_versioning_enabled = False
        # Make sure NAVIGATION_VERSIONING_ENABLED setting is False
        settings_override = UserSettingsHolder(settings._wrapped)
        settings_override.NAVIGATION_VERSIONING_ENABLED = False
        self.wrapped = settings._wrapped
        settings._wrapped = settings_override
        setting_changed.send(
            sender=settings._wrapped.__class__,
            setting='NAVIGATION_VERSIONING_ENABLED', value=False, enter=True)
        super().enable()

    def disable(self):
        super().disable()
        # Reset NAVIGATION_VERSIONING_ENABLED setting
        settings._wrapped = self.wrapped
        del self.wrapped
        # Reset djangocms_versioning_enabled to previous value
        self.navigation_config.djangocms_versioning_enabled = self._prev_versioning_enabled


def get_page_request(page, user):
    request = RequestFactory().get("/")
    request.session = {}
    request.user = user
    request.current_page = page
    mid = ToolbarMiddleware(request)
    mid.process_request(request)
    if hasattr(request, "toolbar"):
        request.toolbar.populate()
    return request


def get_toolbar(content_obj, user=None, **kwargs):
    """Helper method to set up the toolbar
    """
    if not user:
        user = factories.UserFactory(is_staff=True)
    request = get_page_request(
        page=content_obj.page if content_obj else None, user=user
    )
    cms_toolbar = CMSToolbar(request)
    toolbar = NavigationToolbar(
        cms_toolbar.request, toolbar=cms_toolbar, is_current_app=True, app_path="/"
    )
    toolbar.toolbar.set_object(content_obj)
    return toolbar