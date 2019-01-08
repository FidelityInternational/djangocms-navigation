from django.test import TestCase
from django.shortcuts import reverse
from django.contrib import admin

from cms.test_utils.testcases import CMSTestCase
from djangocms_navigation.models import Menu, MenuItem, MenuContent
from djangocms_navigation.test_utils import factories
from djangocms_navigation.admin import MenuItemChangeList, MenuItemAdmin
from django.test import RequestFactory


class MenuContentModelTestCase(CMSTestCase):
    def setUp(self):
        self.superuser = self.get_superuser()

    def test_title(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        self.assertEqual(menu_content.title, "My Title")

    def test_grouper_menu_created(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        self.assertIsInstance(menu_content.menu, Menu)

    def test_root_menuitem_created(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        self.assertIsInstance(menu_content.root, MenuItem)

    def test_string_representation(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        self.assertEqual(str(menu_content), menu_content.title)


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
