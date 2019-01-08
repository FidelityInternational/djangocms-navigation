from django.shortcuts import reverse
from django.test import TestCase

from cms.test_utils.testcases import CMSTestCase

from djangocms_navigation.models import Menu, MenuContent, MenuItem
from djangocms_navigation.test_utils import factories


class MenuContentModelTestCase(TestCase):
    def test_title(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        self.assertEqual(menu_content.title, "My Title")


class MenuContentFormTestCase(CMSTestCase):
    def setUp(self):
        self.user = self.get_superuser()

    def test_menucontent(self):
        self.client.force_login(self.user)
        self.assertEquals(MenuContent.objects.count(), 0)
        post_data = {"title": "My Title"}

        response = self.client.post(
            reverse("admin:djangocms_navigation_menucontent_add"), post_data
        )

        self.assertRedirects(
            response, reverse("admin:djangocms_navigation_menucontent_changelist")
        )
        self.assertEquals(MenuContent.objects.count(), 1)
        self.assertEqual(Menu.objects.count(), 1)
        self.assertEqual(MenuItem.objects.count(), 1)
        self.assertEqual(MenuItem.objects.all()[0].title, "My Title")
