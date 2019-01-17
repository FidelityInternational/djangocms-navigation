from django.test import TestCase

from djangocms_navigation.models import Menu, MenuItem
from djangocms_navigation.test_utils import factories


class MenuModelTestCase(TestCase):
    def test_str(self):
        menu = factories.MenuFactory(identifier='page-about-cats')
        self.assertEqual(str(menu), 'page-about-cats')


class MenuContentModelTestCase(TestCase):

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
