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

    def test_menuitem_changelist(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        self.assertEqual(
            self.site._registry[MenuItem].get_changelist(
                RequestFactory().get("/admin/menuitem/{}/".format(menu_content.root.id))
            ),
            MenuItemChangeList,
        )

    def test_for_result(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        url = reverse(
            "admin:%s_%s_change"
            % (menu_content._meta.app_label, menu_content.root._meta.model_name),
            args=(menu_content.id, menu_content.root.id),
        )
        expected_url = "/en/admin/djangocms_navigation/menuitem/{}/{}/change/".format(
            menu_content.id, menu_content.root.id
        )
        self.assertEqual(url, expected_url)
