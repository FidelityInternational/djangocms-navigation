from unittest.mock import patch

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.shortcuts import reverse
from django.test import RequestFactory, TestCase

from cms.test_utils.testcases import CMSTestCase

from djangocms_navigation.admin import MenuItemAdmin, MenuItemChangeList
from djangocms_navigation.models import Menu, MenuContent, MenuItem
from djangocms_navigation.test_utils import factories
from djangocms_versioning.constants import DRAFT, PUBLISHED, UNPUBLISHED
from djangocms_versioning.helpers import version_list_url

from .utils import UsefulAssertsMixin, VersioningHelpersMixin


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


class MenuContentAdminViewTestCase(CMSTestCase):

    def setUp(self):
        self.client.force_login(self.get_superuser())

    def test_menucontent_add_view(self):
        add_url = reverse("admin:djangocms_navigation_menucontent_add")

        response = self.client.post(add_url, {"title": "My Title"})

        self.assertRedirects(
            response, reverse("admin:djangocms_navigation_menucontent_changelist")
        )
        menu = Menu.objects.get()
        self.assertEqual(menu.identifier, "my-title")
        self.assertEqual(menu.site, Site.objects.get())
        menu_content = MenuContent._base_manager.get()
        self.assertEqual(menu_content.menu, menu)
        self.assertEqual(menu_content.root.title, "My Title")
        self.assertIsNone(menu_content.root.content_type)
        self.assertIsNone(menu_content.root.object_id)

    def test_menucontent_change_view(self):
        menu_content = factories.MenuContentFactory()
        change_url = reverse(
            "admin:djangocms_navigation_menucontent_change", args=(menu_content.pk,)
        )

        response = self.client.get(change_url)

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


class MenuItemModelAdminTestCase(TestCase):
    def setUp(self):
        self.site = admin.AdminSite()
        self.site.register(MenuItem, MenuItemAdmin)
        self.model_admin = self.site._registry[MenuItem]

    def test_get_queryset_filters_by_content_id(self):
        # Multiple menu contents, only the root item of one should be
        # in the queryset
        menu_contents = factories.MenuContentFactory.create_batch(3)
        # This child menu item should be in the queryset
        child_item = factories.ChildMenuItemFactory(parent=menu_contents[0].root)
        # This one should not
        factories.ChildMenuItemFactory(parent=menu_contents[1].root)
        request = RequestFactory().get("/admin/")
        request.menu_content_id = menu_contents[0].pk

        queryset = self.model_admin.get_queryset(request)

        self.assertQuerysetEqual(
            queryset, [menu_contents[0].root.pk, child_item.pk], lambda o: o.pk
        )


class MenuItemAdminChangeViewTestCase(CMSTestCase, UsefulAssertsMixin, VersioningHelpersMixin):
    def setUp(self):
        self.client.force_login(self.get_superuser())

    def test_menuitem_change_view(self):
        menu_content = factories.MenuContentWithVersionFactory(version__state=DRAFT)
        item = factories.ChildMenuItemFactory(parent=menu_content.root)
        change_url = reverse(
            "admin:djangocms_navigation_menuitem_change",
            kwargs={"menu_content_id": menu_content.pk, "object_id": item.pk},
        )
        content_type = ContentType.objects.get(app_label="cms", model="page")
        page = factories.PageContentFactory().page
        data = {
            "title": "My new Title",
            "content_type": content_type.pk,
            "object_id": page.pk,
            "_ref_node_id": menu_content.root.id,
            "numchild": 1,
            "link_target": "_blank",
            "_position": "first-child",
        }

        response = self.client.post(change_url, data)

        # Redirect happened
        redirect_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.pk,)
        )
        self.assertRedirects(response, redirect_url)
        # No menu, menu content or menu item objects were added
        self.assertEqual(Menu.objects.exclude(pk=menu_content.menu.pk).count(), 0)
        self.assertEqual(MenuContent.objects.exclude(pk=menu_content.pk).count(), 0)
        self.assertEqual(
            MenuItem.objects.exclude(pk__in=[menu_content.root.pk, item.pk]).count(), 0
        )
        # Menu object didn't change
        menu = Menu.objects.get()
        self.assertEqual(menu.identifier, menu_content.menu.identifier)
        # Root menu item was changed as per POST data
        item.refresh_from_db()
        self.assertEqual(item.title, "My new Title")
        self.assertEqual(item.content_type, content_type)
        self.assertEqual(item.object_id, page.pk)
        self.assertEqual(item.link_target, "_blank")
        self.assertTrue(item.is_child_of(menu_content.root))

    def test_menuitem_change_view_smoketest_for_versioning_disabled(self):
        with self.disable_versioning():
            menu_content = factories.MenuContentFactory()
            item = factories.ChildMenuItemFactory(parent=menu_content.root)
            change_url = reverse(
                "admin:djangocms_navigation_menuitem_change",
                kwargs={"menu_content_id": menu_content.pk, "object_id": item.pk},
            )
            content_type = ContentType.objects.get(app_label="cms", model="page")
            page = factories.PageContentFactory().page
            data = {
                "title": "My new Title",
                "content_type": content_type.pk,
                "object_id": page.pk,
                "_ref_node_id": menu_content.root.id,
                "numchild": 1,
                "link_target": "_blank",
                "_position": "first-child",
            }

            response = self.client.post(change_url, data)

            # Expected redirect happened
            redirect_url = reverse(
                "admin:djangocms_navigation_menuitem_list", args=(menu_content.pk,)
            )
            self.assertRedirects(response, redirect_url)

    def test_menuitem_change_view_throws_404_on_non_existing_menucontent_get(self):
        change_url = reverse(
            "admin:djangocms_navigation_menuitem_change",
            kwargs={"menu_content_id": 93, "object_id": 91},
        )

        response = self.client.get(change_url)

        self.assertEqual(response.status_code, 404)

    def test_menuitem_change_view_throws_404_on_non_existing_menucontent_post(self):
        change_url = reverse(
            "admin:djangocms_navigation_menuitem_change",
            kwargs={"menu_content_id": 93, "object_id": 91},
        )

        response = self.client.post(change_url)

        self.assertEqual(response.status_code, 404)

    @patch('django.contrib.messages.add_message')
    def test_menuitem_change_view_redirects_if_not_latest_version_get(self, mocked_messages):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=UNPUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=PUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=DRAFT)
        item = factories.ChildMenuItemFactory(parent=version.content.root)
        change_url = reverse(
            "admin:djangocms_navigation_menuitem_change",
            kwargs={"menu_content_id": version.content.pk, "object_id": item.pk},
        )

        response = self.client.get(change_url)

        # Redirect happened and error message displayed
        self.assertRedirectsToVersionList(response, menu)
        self.assertDjangoErrorMessage(
            'Version is not in draft state', mocked_messages)

    @patch('django.contrib.messages.add_message')
    def test_menuitem_change_view_redirects_if_not_latest_version_post(self, mocked_messages):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=UNPUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=PUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=DRAFT)
        item = factories.ChildMenuItemFactory(parent=version.content.root)
        change_url = reverse(
            "admin:djangocms_navigation_menuitem_change",
            kwargs={"menu_content_id": version.content.pk, "object_id": item.pk},
        )
        content_type = ContentType.objects.get(app_label="cms", model="page")
        data = {
            "title": "My new Title",
            "content_type": content_type.pk,
            "object_id": item.content.pk,
            "_ref_node_id": version.content.root.id,
            "numchild": 1,
            "link_target": "_blank",
            "_position": "first-child",
        }

        response = self.client.post(change_url, data)

        # Redirect happened and error message displayed
        self.assertRedirectsToVersionList(response, menu)
        self.assertDjangoErrorMessage(
            'Version is not in draft state', mocked_messages)
        # Menu item object was not changed
        item.refresh_from_db()
        self.assertNotEqual(item.title, "My new Title")


class MenuItemAdminAddViewTestCase(CMSTestCase, VersioningHelpersMixin):
    def setUp(self):
        self.client.force_login(self.get_superuser())

    def test_menuitem_add_view(self):
        menu_content = factories.MenuContentWithVersionFactory()
        add_url = reverse(
            "admin:djangocms_navigation_menuitem_add", args=(menu_content.id,)
        )
        content_type = ContentType.objects.get(app_label="cms", model="page")
        page = factories.PageContentFactory().page
        data = {
            "title": "My new Title",
            "content_type": content_type.pk,
            "object_id": page.pk,
            "_ref_node_id": menu_content.root.id,
            "numchild": 1,
            "link_target": "_blank",
            "_position": "first-child",
        }

        response = self.client.post(add_url, data)

        self.assertRedirects(
            response,
            reverse(
                "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
            ),
        )
        # No menu or menu content objects were added
        self.assertEqual(Menu.objects.exclude(pk=menu_content.menu.pk).count(), 0)
        self.assertEqual(MenuContent.objects.exclude(pk=menu_content.pk).count(), 0)
        # A child menu item object was added
        new_child = MenuItem.objects.exclude(pk=menu_content.root.pk).get()
        self.assertEqual(new_child.title, "My new Title")
        self.assertEqual(new_child.content_type, content_type)
        self.assertEqual(new_child.object_id, page.pk)
        self.assertEqual(new_child.link_target, "_blank")
        self.assertTrue(new_child.is_child_of(menu_content.root))

    def test_menuitem_add_view_smoketest_for_versioning_disabled(self):
        with self.disable_versioning():
            menu_content = factories.MenuContentFactory()
            add_url = reverse(
                "admin:djangocms_navigation_menuitem_add", args=(menu_content.id,)
            )
            content_type = ContentType.objects.get(app_label="cms", model="page")
            page = factories.PageContentFactory().page
            data = {
                "title": "My new Title",
                "content_type": content_type.pk,
                "object_id": page.pk,
                "_ref_node_id": menu_content.root.id,
                "numchild": 1,
                "link_target": "_blank",
                "_position": "first-child",
            }

            response = self.client.post(add_url, data)

            self.assertRedirects(
                response,
                reverse(
                    "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
                ),
            )

    def test_menuitem_add_view_throws_404_on_non_existing_menucontent_get(self):
        add_url = reverse(
            "admin:djangocms_navigation_menuitem_add", args=(83,)
        )

        response = self.client.get(add_url)

        self.assertEqual(response.status_code, 404)

    def test_menuitem_add_view_throws_404_on_non_existing_menucontent_post(self):
        add_url = reverse(
            "admin:djangocms_navigation_menuitem_add", args=(83,)
        )

        response = self.client.post(add_url)

        self.assertEqual(response.status_code, 404)


class MenuItemAdminChangeListViewTestCase(CMSTestCase, VersioningHelpersMixin):
    def setUp(self):
        self.client.force_login(self.get_superuser())

    def test_menuitem_changelist(self):
        menu_content = factories.MenuContentWithVersionFactory()
        factories.ChildMenuItemFactory.create_batch(5, parent=menu_content.root)
        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )

        response = self.client.get(list_url)

        # Just a smoke test
        self.assertEqual(response.status_code, 200)

    def test_menuitem_changelist_view_smoketest_for_versioning_disabled(self):
        with self.disable_versioning():
            menu_content = factories.MenuContentFactory()
            factories.ChildMenuItemFactory.create_batch(5, parent=menu_content.root)
            list_url = reverse(
                "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
            )

            response = self.client.get(list_url)

            # Just a smoke test
            self.assertEqual(response.status_code, 200)

    def test_menuitem_changelist_throws_404_on_non_existing_menucontent(self):
        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(881,)
        )

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, 404)

    def test_menuitem_changelist_contains_add_url(self):
        menu_content = factories.MenuContentFactory()
        factories.ChildMenuItemFactory.create_batch(5, parent=menu_content.root)
        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )

        response = self.client.get(list_url)

        add_url = reverse(
            "admin:djangocms_navigation_menuitem_add", args=(menu_content.id,)
        )
        self.assertIn(add_url, str(response.content))

    def test_menuitem_changelist_contains_version_list_url(self):
        menu_content = factories.MenuContentFactory()
        factories.ChildMenuItemFactory.create_batch(5, parent=menu_content.root)
        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )

        response = self.client.get(list_url)

        self.assertIn(version_list_url(menu_content), str(response.content))


class MenuItemAdminMoveNodeViewTestCase(CMSTestCase, VersioningHelpersMixin):
    def setUp(self):
        self.client.force_login(self.get_superuser())

    def test_menuitem_move_node_smoke_test(self):
        menu_content = factories.MenuContentWithVersionFactory()
        child = factories.ChildMenuItemFactory(parent=menu_content.root)
        child_of_child = factories.ChildMenuItemFactory(parent=child)
        move_url = reverse(
            "admin:djangocms_navigation_menuitem_move_node", args=(menu_content.id,)
        )
        data = {
            "node_id": child_of_child.pk,
            "sibling_id": menu_content.root.pk,
            "as_child": 1,
        }

        response = self.client.post(move_url, data=data)

        self.assertEqual(response.status_code, 200)

    @patch("django.contrib.messages.error")
    def test_menuitem_move_node_cant_move_outside_of_root(self, mocked_messages):
        menu_content = factories.MenuContentFactory()
        child = factories.ChildMenuItemFactory(parent=menu_content.root)
        move_url = reverse(
            "admin:djangocms_navigation_menuitem_move_node", args=(menu_content.id,)
        )
        data = {"node_id": child.pk, "parent_id": 0}

        response = self.client.post(move_url, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(
            mocked_messages.call_args[0][1],
            "Cannot move a node outside of the root menu node",
        )

    def test_menuitem_move_node_view_smoketest_for_versioning_disabled(self):
        with self.disable_versioning():
            menu_content = factories.MenuContentFactory()
            child = factories.ChildMenuItemFactory(parent=menu_content.root)
            child_of_child = factories.ChildMenuItemFactory(parent=child)
            move_url = reverse(
                "admin:djangocms_navigation_menuitem_move_node", args=(menu_content.id,)
            )
            data = {
                "node_id": child_of_child.pk,
                "sibling_id": menu_content.root.pk,
                "as_child": 1,
            }

            response = self.client.post(move_url, data=data)

            self.assertEqual(response.status_code, 200)


class MenuItemPermissionTestCase(CMSTestCase):
    def test_change_view_redirects_to_login_if_anonymous_user(self):
        menu_content = factories.MenuContentFactory()
        item = factories.ChildMenuItemFactory(parent=menu_content.root)
        change_url = reverse(
            "admin:djangocms_navigation_menuitem_change",
            kwargs={"menu_content_id": menu_content.pk, "object_id": item.pk},
        )
        content_type = ContentType.objects.get(app_label="cms", model="page")
        page = factories.PageContentFactory().page
        data = {
            "title": "My new Title",
            "content_type": content_type.pk,
            "object_id": page.pk,
            "_ref_node_id": menu_content.root.id,
            "numchild": 1,
            "link_target": "_blank",
            "_position": "first-child",
        }

        # For POST
        response = self.client.post(change_url, data)
        redirect_url = reverse("admin:login") + "?next=" + change_url
        self.assertRedirects(response, redirect_url)

        # For GET
        response = self.client.get(change_url)
        self.assertRedirects(response, redirect_url)

    def test_change_view_redirects_to_login_if_non_staff_user(self):
        user = factories.UserFactory(is_superuser=False, is_staff=False)
        self.client.force_login(user)

        menu_content = factories.MenuContentFactory()
        item = factories.ChildMenuItemFactory(parent=menu_content.root)
        change_url = reverse(
            "admin:djangocms_navigation_menuitem_change",
            kwargs={"menu_content_id": menu_content.pk, "object_id": item.pk},
        )
        content_type = ContentType.objects.get(app_label="cms", model="page")
        page = factories.PageContentFactory().page
        data = {
            "title": "My new Title",
            "content_type": content_type.pk,
            "object_id": page.pk,
            "_ref_node_id": menu_content.root.id,
            "numchild": 1,
            "link_target": "_blank",
            "_position": "first-child",
        }

        # For POST
        response = self.client.post(change_url, data)
        redirect_url = reverse("admin:login") + "?next=" + change_url
        self.assertRedirects(response, redirect_url)

        # For GET
        response = self.client.get(change_url)
        self.assertRedirects(response, redirect_url)

    def test_add_view_redirects_to_login_if_anonymous_user(self):
        menu_content = factories.MenuContentFactory()
        add_url = reverse(
            "admin:djangocms_navigation_menuitem_add", args=(menu_content.id,)
        )
        content_type = ContentType.objects.get(app_label="cms", model="page")
        page = factories.PageContentFactory().page
        data = {
            "title": "My new Title",
            "content_type": content_type.pk,
            "object_id": page.pk,
            "_ref_node_id": menu_content.root.id,
            "numchild": 1,
            "link_target": "_blank",
            "_position": "first-child",
        }

        # For POST
        response = self.client.post(add_url, data)
        redirect_url = reverse("admin:login") + "?next=" + add_url
        self.assertRedirects(response, redirect_url)

        # For GET
        response = self.client.get(add_url)
        self.assertRedirects(response, redirect_url)

    def test_add_view_redirects_to_login_if_non_staff_user(self):
        user = factories.UserFactory(is_superuser=False, is_staff=False)
        self.client.force_login(user)

        menu_content = factories.MenuContentFactory()
        add_url = reverse(
            "admin:djangocms_navigation_menuitem_add", args=(menu_content.id,)
        )
        content_type = ContentType.objects.get(app_label="cms", model="page")
        page = factories.PageContentFactory().page
        data = {
            "title": "My new Title",
            "content_type": content_type.pk,
            "object_id": page.pk,
            "_ref_node_id": menu_content.root.id,
            "numchild": 1,
            "link_target": "_blank",
            "_position": "first-child",
        }

        # For POST
        response = self.client.post(add_url, data)
        redirect_url = reverse("admin:login") + "?next=" + add_url
        self.assertRedirects(response, redirect_url)

        # For GET
        response = self.client.get(add_url)
        self.assertRedirects(response, redirect_url)

    def test_changelist_view_redirects_to_login_if_anonymous_user(self):
        menu_content = factories.MenuContentFactory()
        factories.ChildMenuItemFactory.create_batch(5, parent=menu_content.root)
        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )

        response = self.client.get(list_url)

        redirect_url = reverse("admin:login") + "?next=" + list_url
        self.assertRedirects(response, redirect_url)

    def test_changelist_view_redirects_to_login_if_non_staff_user(self):
        user = factories.UserFactory(is_superuser=False, is_staff=False)
        self.client.force_login(user)

        menu_content = factories.MenuContentFactory()
        factories.ChildMenuItemFactory.create_batch(5, parent=menu_content.root)
        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )

        response = self.client.get(list_url)

        redirect_url = reverse("admin:login") + "?next=" + list_url
        self.assertRedirects(response, redirect_url)

    def test_move_node_view_redirects_to_login_if_anonymous_user(self):
        menu_content = factories.MenuContentFactory()
        child = factories.ChildMenuItemFactory(parent=menu_content.root)
        child_of_child = factories.ChildMenuItemFactory(parent=child)
        move_url = reverse(
            "admin:djangocms_navigation_menuitem_move_node", args=(menu_content.id,)
        )
        data = {
            "node_id": child_of_child.pk,
            "sibling_id": menu_content.root.pk,
            "as_child": 1,
        }

        # For POST
        response = self.client.post(move_url, data=data)
        redirect_url = reverse("admin:login") + "?next=" + move_url
        self.assertRedirects(response, redirect_url)

        # For GET
        response = self.client.get(move_url)
        self.assertRedirects(response, redirect_url)

    def test_move_node_view_redirects_to_login_if_non_staff_user(self):
        user = factories.UserFactory(is_superuser=False, is_staff=False)
        self.client.force_login(user)

        menu_content = factories.MenuContentFactory()
        child = factories.ChildMenuItemFactory(parent=menu_content.root)
        child_of_child = factories.ChildMenuItemFactory(parent=child)
        move_url = reverse(
            "admin:djangocms_navigation_menuitem_move_node", args=(menu_content.id,)
        )
        data = {
            "node_id": child_of_child.pk,
            "sibling_id": menu_content.root.pk,
            "as_child": 1,
        }

        # For POST
        response = self.client.post(move_url, data=data)
        redirect_url = reverse("admin:login") + "?next=" + move_url
        self.assertRedirects(response, redirect_url)

        # For GET
        response = self.client.get(move_url)
        self.assertRedirects(response, redirect_url)

    def test_has_add_permission_returns_false_for_invalid_request(self):
        """
        has_add_permission returns False for request which doesnt contain
        menu_content_id
        """
        model_admin = MenuItemAdmin(MenuItem, admin.AdminSite())
        request = RequestFactory().get("/admin")
        request.user = self.get_superuser()
        self.assertFalse(model_admin.has_add_permission(request))

    def test_has_change_permission_returns_false_for_invalid_request(self):
        """
        has_change_permission returns False for request which doesnt contain
        menu_content_id
        """
        model_admin = MenuItemAdmin(MenuItem, admin.AdminSite())
        request = RequestFactory().get("/admin")
        request.user = self.get_superuser()
        self.assertFalse(model_admin.has_change_permission(request))
