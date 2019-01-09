from django.contrib import admin
from django.contrib.sites.models import Site
from django.shortcuts import reverse
from django.test import RequestFactory, TestCase

from cms.test_utils.testcases import CMSTestCase

from djangocms_navigation.admin import MenuItemAdmin, MenuItemChangeList
from djangocms_navigation.models import Menu, MenuContent, MenuItem
from djangocms_navigation.test_utils import factories


class MenuItemChangelistTestCase(TestCase):
    def setUp(self):
        self.site = admin.AdminSite()
        self.site.register(MenuItem, MenuItemAdmin)

    def _get_changelist_instance(self, menu_content):
        """Helper to instantiate a MenuItemChangeList simply"""
        request = RequestFactory().get("/admin/djangocms_navigation/")
        request.menu_content_id = menu_content.pk
        model_admin = self.site._registry[MenuItem]
        return MenuItemChangeList(
            request,
            MenuItem,
            None,
            None,
            None,
            None,
            None,
            None,
            100,
            250,
            None,
            model_admin,
        )

    def test_menuitem_changelist(self):
        request = RequestFactory().get("/admin/djangocms_navigation/menuitem/36/")
        self.assertEqual(
            self.site._registry[MenuItem].get_changelist(request), MenuItemChangeList
        )

    def test_for_url_for_result(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        changelist = self._get_changelist_instance(menu_content)

        url = changelist.url_for_result(menu_content.root)

        expected_url = "/en/admin/djangocms_navigation/menuitem/{}/{}/change/".format(
            menu_content.pk, menu_content.root.pk
        )
        self.assertEqual(url, expected_url)


class MenuContentAdminTestCase(CMSTestCase):
    def test_menucontent_add_view(self):
        self.client.force_login(self.get_superuser())
        add_url = reverse("admin:djangocms_navigation_menucontent_add")

        response = self.client.post(add_url, {"title": "My Title"})

        self.assertRedirects(
            response, reverse("admin:djangocms_navigation_menucontent_changelist")
        )
        menu = Menu.objects.get()
        self.assertEqual(menu.identifier, "my-title")
        self.assertEqual(menu.site, Site.objects.get())
        menu_content = MenuContent.objects.get()
        self.assertEqual(menu_content.menu, menu)
        self.assertEqual(menu_content.root.title, "My Title")
        self.assertIsNone(menu_content.root.content_type)
        self.assertIsNone(menu_content.root.object_id)

    def test_menucontent_change_view(self):
        self.client.force_login(self.get_superuser())
        menu_content = factories.MenuContentFactory()
        change_url = reverse(
            "admin:djangocms_navigation_menucontent_change", args=(menu_content.pk,)
        )

        response = self.client.post(change_url, {"title": "My Title"})

        # Redirect happened
        redirect_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.pk,)
        )
        self.assertRedirects(response, redirect_url)
        # No menu objects were added
        self.assertEqual(Menu.objects.exclude(pk=menu_content.menu.pk).count(), 0)
        self.assertEqual(MenuContent.objects.exclude(pk=menu_content.pk).count(), 0)
        self.assertEqual(MenuItem.objects.exclude(pk=menu_content.root.pk).count(), 0)
        # The data sent in POST did not change any values
        menu = Menu.objects.get()
        self.assertNotEqual(menu.identifier, "my-title")
        root = MenuItem.objects.get()
        self.assertNotEqual(root.title, "My Title")
