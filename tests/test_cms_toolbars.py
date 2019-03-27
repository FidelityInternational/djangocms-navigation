from django.contrib.auth.models import Permission
from django.shortcuts import reverse
from django.test import TestCase
from django.test.client import RequestFactory

from cms.middleware.toolbar import ToolbarMiddleware
from cms.toolbar.items import SideframeItem
from cms.toolbar.toolbar import CMSToolbar

from djangocms_navigation.cms_toolbars import NavigationToolbar
from djangocms_navigation.test_utils import factories


class TestCMSToolbars(TestCase):
    def _get_page_request(self, page, user):
        request = RequestFactory().get("/")
        request.session = {}
        request.user = user
        request.current_page = page
        mid = ToolbarMiddleware()
        mid.process_request(request)
        if hasattr(request, "toolbar"):
            request.toolbar.populate()
        return request

    def _get_toolbar(self, content_obj, user=None, **kwargs):
        """Helper method to set up the toolbar
        """
        if not user:
            user = factories.UserFactory(is_staff=True)
        request = self._get_page_request(
            page=content_obj.page if content_obj else None, user=user
        )
        cms_toolbar = CMSToolbar(request)
        toolbar = NavigationToolbar(
            cms_toolbar.request, toolbar=cms_toolbar, is_current_app=True, app_path="/"
        )
        toolbar.toolbar.set_object(content_obj)
        return toolbar

    def _find_menu_item(self, name, toolbar):
        for left_item in toolbar.get_left_items():
            for menu_item in left_item.items:
                try:
                    if menu_item.name == name:
                        return menu_item
                # Break item has no attribute `name`
                except AttributeError:
                    pass

    def test_navigation_menu_added_to_admin_menu(self):
        user = factories.UserFactory()
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="djangocms_navigation",
                codename="change_menucontent",
            )
        )
        page_content = factories.PageContentFactory()
        toolbar = self._get_toolbar(page_content, preview_mode=True, user=user)
        toolbar.populate()
        toolbar.post_template_populate()
        cms_toolbar = toolbar.toolbar
        navigation_menu_item = self._find_menu_item("Navigation...", cms_toolbar)
        url = reverse("admin:djangocms_navigation_menucontent_changelist")

        self.assertIsNotNone(navigation_menu_item)
        self.assertIsInstance(navigation_menu_item, SideframeItem)
        self.assertEqual(navigation_menu_item.url, url)

    def test_navigation_menu_not_added_to_admin_menu_if_user_doesnt_have_permissions(
        self
    ):
        user = factories.UserFactory()
        page_content = factories.PageContentFactory()
        toolbar = self._get_toolbar(page_content, preview_mode=True, user=user)
        toolbar.populate()
        toolbar.post_template_populate()
        cms_toolbar = toolbar.toolbar
        navigation_menu_item = self._find_menu_item("Navigation...", cms_toolbar)
        url = reverse("admin:djangocms_navigation_menucontent_changelist")

        self.assertIsNone(navigation_menu_item)
