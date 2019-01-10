from django.test import TestCase

from djangocms_navigation.test_utils import factories


class MenuContentModelTestCase(TestCase):
    def test_title(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        self.assertEqual(menu_content.title, "My Title")
