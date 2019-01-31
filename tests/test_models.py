from django.test import TestCase

from djangocms_navigation.test_utils import factories


class MenuModelTestCase(TestCase):
    def test_str(self):
        menu = factories.MenuFactory(identifier='page-about-cats')
        self.assertEqual(str(menu), 'page-about-cats')

    def test_root_id(self):
        menu = factories.MenuContentWithVersionFactory(
            menu__identifier='black-cats').menu
        self.assertEqual(menu.root_id, 'root-black-cats')


class MenuContentModelTestCase(TestCase):

    def test_title(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        self.assertEqual(menu_content.title, "My Title")

    def test_string_representation(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        self.assertEqual(str(menu_content), menu_content.title)
