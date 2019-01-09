from django.contrib import admin
from django.shortcuts import reverse
from django.test import RequestFactory

from cms.test_utils.testcases import CMSTestCase

from djangocms_navigation.admin import MenuItemAdmin, MenuItemChangeList
from djangocms_navigation.models import MenuItem
from djangocms_navigation.test_utils import factories


class MenuItemChangelistTestCase(CMSTestCase):
    def setUp(self):
        self.site = admin.AdminSite()
        self.site.register(MenuItem, MenuItemAdmin)

    def _get_changelist_instance(self, menu_content):
        """Helper to instantiate a MenuItemChangeList simply"""
        request = RequestFactory().get("/admin/djangocms_navigation/")
        request.menu_content_id = menu_content.pk
        model_admin = self.site._registry[MenuItem]
        return MenuItemChangeList(
            request, MenuItem, None, None, None, None, None, None, 100,
            250, None, model_admin
        )

    def test_menuitem_changelist(self):
        request = RequestFactory().get("/admin/djangocms_navigation/menuitem/36/")
        self.assertEqual(
            self.site._registry[MenuItem].get_changelist(request),
            MenuItemChangeList,
        )

    def test_for_url_for_result(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        changelist = self._get_changelist_instance(menu_content)

        url = changelist.url_for_result(menu_content.root)

        expected_url = "/en/admin/djangocms_navigation/menuitem/{}/{}/change/".format(
            menu_content.pk, menu_content.root.pk
        )
        self.assertEqual(url, expected_url)
