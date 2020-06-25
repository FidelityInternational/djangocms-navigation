from io import StringIO
from unittest.mock import patch

import django
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.contrib.sites.models import Site
from django.shortcuts import reverse
from django.test import RequestFactory, TestCase

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.constants import DRAFT, PUBLISHED, UNPUBLISHED
from djangocms_versioning.exceptions import ConditionFailed
from djangocms_versioning.helpers import version_list_url

from djangocms_navigation import admin as nav_admin
from djangocms_navigation.admin import (
    MenuContentAdmin,
    MenuItemAdmin,
    MenuItemChangeList,
)
from djangocms_navigation.models import Menu, MenuContent, MenuItem
from djangocms_navigation.test_utils import factories
from lxml import etree

from .utils import UsefulAssertsMixin, disable_versioning_for_navigation


version = list(map(int, django.__version__.split('.')))
GTE_DJ21 = version[0] >= 2 and version[1] >= 1


class MenuItemChangelistTestCase(CMSTestCase):
    def setUp(self):
        self.user = self.get_superuser()
        self.site = admin.AdminSite()
        self.site.register(MenuItem, MenuItemAdmin)

    def _get_changelist_instance(self, menu_content):
        """Helper to instantiate a MenuItemChangeList simply"""
        request = RequestFactory().get("/admin/djangocms_navigation/")
        request.user = self.user
        request.menu_content_id = menu_content.pk
        request.user = self.get_superuser()
        model_admin = self.site._registry[MenuItem]
        import pdb
        pdb.set_trace()
        admin_field = "title"

        args = [
            request,  # request
            MenuItem,  # model
            None,  # list_display
            None,  # list_display_links
            [admin_field, ],  # list_filter
            None,  # date_hierarchy
            None,  # search_fields
            None,  # list_select_related
            100,  # list_per_page
            250,  # list_max_show_all
            None,  # list_editable
            model_admin,  # model_admin
            admin_field,  # sortable_by
        ]
        if not GTE_DJ21:
            args.pop()

        return MenuItemChangeList(*args)

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
        self.admin_site = admin.AdminSite()
        self.admin_site.register(MenuContent, MenuContentAdmin)

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
        menu_content = factories.MenuContentWithVersionFactory()
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

    def test_menucontent_change_view_limited_to_site(self):
        """
        The admin change list is limited to show only the menus for the current site.
        No other menus should be shown that belong to other sites.
        """
        site_2 = Site.objects.create(domain="site_2.com", name="site_2")
        site_3 = Site.objects.create(domain="site_3.com", name="site_3")
        menu_1 = factories.MenuFactory(site=site_2)
        menu_2 = factories.MenuFactory(site=site_3)
        site_2_menu_version = factories.MenuVersionFactory(content__menu=menu_1, state=PUBLISHED)
        site_3_menu_version = factories.MenuVersionFactory(content__menu=menu_2, state=PUBLISHED)
        menu_content_admin = self.admin_site._registry[MenuContent]

        # Site 1 has no menus and should be empty
        with self.settings(SITE_ID=1):
            request = RequestFactory().get("/admin/djangocms_navigation/menucontent/")
            site1_query_result = menu_content_admin.get_queryset(request)

            self.assertEqual(site1_query_result.count(), 0)

        # Site 2 has a menu and should it should only be the one created for that site
        with self.settings(SITE_ID=site_2.pk):
            request = RequestFactory().get("/admin/djangocms_navigation/menucontent/")
            request.site = site_2
            site2_query_result = menu_content_admin.get_queryset(request)

            self.assertEqual(site2_query_result.count(), 1)
            self.assertEqual(site2_query_result.first(), site_2_menu_version.content)

        # Site 3 has a menu and should it should only be the one created for that site
        with self.settings(SITE_ID=site_3.pk):
            request = RequestFactory().get("/admin/djangocms_navigation/menucontent/")
            request.site = site_3
            site3_query_result = menu_content_admin.get_queryset(request)

            self.assertEqual(site3_query_result.count(), 1)
            self.assertEqual(site3_query_result.first(), site_3_menu_version.content)

    @patch("djangocms_navigation.cms_config.djangocms_versioning_enabled", False)
    def test_list_display_without_version_locking(self):
        request = self.get_request("/")
        model_admin = self.site._registry[MenuContent]
        request.user = self.get_superuser()
        func = model_admin._list_actions(self.get_request("/admin"))



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


class MenuItemAdminVersionLocked(CMSTestCase, UsefulAssertsMixin):

    def setUp(self):
        self.menu_content = factories.MenuContentWithVersionFactory(version__state=DRAFT)
        self.item = factories.ChildMenuItemFactory(parent=self.menu_content.root)

        self.change_url = reverse(
            "admin:djangocms_navigation_menuitem_change",
            kwargs={"menu_content_id": self.menu_content.pk, "object_id": self.item.pk}
        )
        self.client.force_login(self.get_superuser())

        # moving a node
        menu_content = factories.MenuContentWithVersionFactory()
        self.child = factories.ChildMenuItemFactory(parent=menu_content.root)
        self.child_of_child = factories.ChildMenuItemFactory(parent=self.child)
        self.move_url = reverse(
            "admin:djangocms_navigation_menuitem_move_node", args=(menu_content.id,)
        )
        self.data = {
            "node_id": self.child_of_child.pk,
            "sibling_id": menu_content.root.pk,
            "as_child": 1,
        }

    def test_visit_change_view_when_node_is_version_locked_fails(self):
        """It fails as super user is not the person who created the version"""
        response = self.client.get(self.change_url)
        msg = list(get_messages(response.wsgi_request))

        if nav_admin.using_version_lock:
            actual_message = msg[0].message
            expected_message = "The item is currently locked or you don't have permission to change it"
            status_code = 302
        else:
            actual_message = msg
            expected_message = []
            status_code = 200

        self.assertEquals(actual_message, expected_message)
        self.assertEquals(response.status_code, status_code)

    def test_moving_node_that_is_version_locked_fails(self):
        """
        Check that moving node does not wotk if version is locked, also ensure it works if version locking not enabled
        """
        response = self.client.post(self.move_url, data=self.data)
        content = response.content.decode('utf-8')

        if nav_admin.using_version_lock:
            msg = "The item is currently locked or you don't have permission to change it"
            response_code = 400
        else:
            msg = "OK"
            response_code = 200

        self.assertEquals(response.status_code, response_code)
        self.assertEquals(content, msg)

    @patch('djangocms_navigation.admin.using_version_lock', False)
    def test_moving_node_version_lock_not_installed_works_without_error(self):
        response = self.client.post(self.move_url, data=self.data)

        self.assertEquals(response.status_code, 200)
        self.child.refresh_from_db()
        self.child_of_child.refresh_from_db()
        self.assertTrue(self.child_of_child.is_sibling_of(self.child))


class MenuItemAdminChangeViewTestCase(CMSTestCase, UsefulAssertsMixin):
    def setUp(self):
        self.client.force_login(self.get_superuser())

    def test_menuitem_change_view(self):
        menu_content = factories.MenuContentWithVersionFactory(
            version__state=DRAFT, version__created_by=self.get_superuser()
        )
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

    @disable_versioning_for_navigation()
    def test_menuitem_change_view_smoketest_for_versioning_disabled(self):
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

    @patch("django.contrib.messages.error")
    @patch("djangocms_versioning.models.Version.check_modify")
    def test_menuitem_change_view_does_modify_check_on_version(
        self, mocked_check, mocked_messages
    ):
        mocked_check.side_effect = ConditionFailed(
            "Go look at some cat pictures instead"
        )
        menu_content = factories.MenuContentWithVersionFactory(
            version__created_by=self.get_superuser()
        )
        item = factories.ChildMenuItemFactory(parent=menu_content.root)
        change_url = reverse(
            "admin:djangocms_navigation_menuitem_change",
            kwargs={"menu_content_id": menu_content.pk, "object_id": item.pk},
        )

        response = self.client.get(change_url)

        # Redirect happened, error message displayed and check modify used
        self.assertRedirectsToVersionList(response, menu_content.menu)
        self.assertDjangoErrorMessage(
            "Go look at some cat pictures instead", mocked_messages
        )
        mocked_check.assert_called_once_with(self.get_superuser())

    @patch("django.contrib.messages.error")
    def test_menuitem_change_view_redirects_if_not_latest_version_get(
        self, mocked_messages
    ):
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
        self.assertDjangoErrorMessage("Version is not a draft", mocked_messages)

    @patch("django.contrib.messages.error")
    def test_menuitem_change_view_redirects_if_not_latest_version_post(
        self, mocked_messages
    ):
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
        self.assertDjangoErrorMessage("Version is not a draft", mocked_messages)
        # Menu item object was not changed
        item.refresh_from_db()
        self.assertNotEqual(item.title, "My new Title")


class MenuItemAdminAddViewTestCase(CMSTestCase, UsefulAssertsMixin):
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

    @disable_versioning_for_navigation()
    def test_menuitem_add_view_smoketest_for_versioning_disabled(self):
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
        add_url = reverse("admin:djangocms_navigation_menuitem_add", args=(83,))

        response = self.client.get(add_url)

        self.assertEqual(response.status_code, 404)

    def test_menuitem_add_view_throws_404_on_non_existing_menucontent_post(self):
        add_url = reverse("admin:djangocms_navigation_menuitem_add", args=(83,))

        response = self.client.post(add_url)

        self.assertEqual(response.status_code, 404)

    @patch("django.contrib.messages.error")
    @patch("djangocms_versioning.models.Version.check_modify")
    def test_menuitem_add_view_does_modify_check_on_version(
        self, mocked_check, mocked_messages
    ):
        mocked_check.side_effect = ConditionFailed(
            "Go look at some cat pictures instead"
        )
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

        # Redirect happened, error message displayed and check modify used
        self.assertRedirectsToVersionList(response, menu_content.menu)
        self.assertDjangoErrorMessage(
            "Go look at some cat pictures instead", mocked_messages
        )
        mocked_check.assert_called_once_with(self.get_superuser())

    @patch("django.contrib.messages.error")
    def test_menuitem_add_view_redirects_if_not_latest_version_get(
        self, mocked_messages
    ):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=UNPUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=PUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=DRAFT)
        add_url = reverse(
            "admin:djangocms_navigation_menuitem_add", args=(version.content.id,)
        )

        response = self.client.get(add_url)

        # Redirect happened and error message displayed
        self.assertRedirectsToVersionList(response, menu)
        self.assertDjangoErrorMessage("Version is not a draft", mocked_messages)

    @patch("django.contrib.messages.error")
    def test_menuitem_add_view_redirects_if_not_latest_version_post(
        self, mocked_messages
    ):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=UNPUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=PUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=DRAFT)
        add_url = reverse(
            "admin:djangocms_navigation_menuitem_add", args=(version.content.id,)
        )
        content_type = ContentType.objects.get(app_label="cms", model="page")
        page = factories.PageContentFactory().page
        data = {
            "title": "My new Title",
            "content_type": content_type.pk,
            "object_id": page.pk,
            "_ref_node_id": version.content.root.id,
            "numchild": 1,
            "link_target": "_blank",
            "_position": "first-child",
        }

        response = self.client.post(add_url, data)

        # Redirect happened and error message displayed
        self.assertRedirectsToVersionList(response, menu)
        self.assertDjangoErrorMessage("Version is not a draft", mocked_messages)
        # Menu item object was not added
        self.assertEqual(MenuItem.objects.filter(title="My new Title").count(), 0)

    def test_menuitem_changelist_should_have_get_url_column(self):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=PUBLISHED)
        mock_request = RequestFactory()
        ma = MenuItemAdmin(MenuItem, admin.AdminSite())
        add_url = reverse(
            "admin:djangocms_navigation_menuitem_add", args=(version.content.id,)
        )
        content_type = ContentType.objects.get(app_label="cms", model="page")
        page = factories.PageContentFactory().page
        data = {
            "title": "My new Title",
            "content_type": content_type.pk,
            "object_id": page.pk,
            "_ref_node_id": version.content.root.id,
            "numchild": 1,
            "link_target": "_blank",
            "_position": "first-child",
        }
        self.client.post(add_url, data)
        self.assertEqual(len(ma.get_list_display(mock_request)), 2)
        self.assertIn("get_object_url", ma.get_list_display(mock_request))


class MenuItemAdminChangeListViewTestCase(CMSTestCase, UsefulAssertsMixin):
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

    @disable_versioning_for_navigation()
    def test_menuitem_changelist_view_smoketest_for_versioning_disabled(self):
        menu_content = factories.MenuContentFactory()
        factories.ChildMenuItemFactory.create_batch(5, parent=menu_content.root)
        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, 200)

    def test_menuitem_changelist_throws_404_on_non_existing_menucontent(self):
        list_url = reverse("admin:djangocms_navigation_menuitem_list", args=(881,))

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, 404)

    def test_menuitem_changelist_contains_add_url(self):
        menu_content = factories.MenuContentWithVersionFactory()
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
        menu_content = factories.MenuContentWithVersionFactory()
        factories.ChildMenuItemFactory.create_batch(5, parent=menu_content.root)
        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )

        response = self.client.get(list_url)

        self.assertIn(version_list_url(menu_content), str(response.content))

    @patch("django.contrib.messages.error")
    @patch("djangocms_versioning.models.Version.check_modify")
    def test_menuitem_changelist_does_modify_check_on_version(
        self, mocked_check, mocked_messages
    ):
        mocked_check.side_effect = ConditionFailed(
            "Go look at some cat pictures instead"
        )
        menu_content = factories.MenuContentWithVersionFactory()
        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )

        response = self.client.get(list_url)

        # Redirect happened, error message displayed and check modify used
        self.assertRedirectsToVersionList(response, menu_content.menu)
        self.assertDjangoErrorMessage(
            "Go look at some cat pictures instead", mocked_messages
        )
        mocked_check.assert_called_once_with(self.get_superuser())

    @patch("django.contrib.messages.error")
    def test_menuitem_changelist_redirects_if_not_latest_version(self, mocked_messages):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=UNPUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=PUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=DRAFT)
        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(version.content.id,)
        )

        response = self.client.get(list_url)

        # Redirect happened and error message displayed
        self.assertRedirectsToVersionList(response, menu)
        self.assertDjangoErrorMessage("Version is not a draft", mocked_messages)


class MenuItemAdminMoveNodeViewTestCase(CMSTestCase):
    def setUp(self):
        self.user = self.get_superuser()
        self.client.force_login(self.user)

    def test_menuitem_move_node_smoke_test(self):
        menu_content = factories.MenuContentWithVersionFactory(version__created_by=self.user)
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
        child.refresh_from_db()
        child_of_child.refresh_from_db()
        self.assertTrue(child_of_child.is_sibling_of(child))

    @patch("django.contrib.messages.error")
    def test_menuitem_move_node_cant_move_outside_of_root(self, mocked_messages):
        menu_content = factories.MenuContentWithVersionFactory(version__created_by=self.user)
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

    @disable_versioning_for_navigation()
    def test_menuitem_move_node_view_smoketest_for_versioning_disabled(self):
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

    @patch("django.contrib.messages.error")
    @patch("djangocms_versioning.models.Version.check_modify")
    def test_menuitem_move_node_does_modify_check_on_version(
        self, mocked_check, mocked_messages
    ):
        mocked_check.side_effect = ConditionFailed(
            "Go look at some cat pictures instead"
        )
        menu_content = factories.MenuContentWithVersionFactory(version__created_by=self.user)
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

        # 400 response with error message that came from version.check_modify
        self.assertEqual(response.status_code, 400)
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(
            mocked_messages.call_args[0][1], "Go look at some cat pictures instead"
        )
        self.assertEqual(b"Go look at some cat pictures instead", response.content)
        mocked_check.assert_called_once_with(self.get_superuser())

    @patch("django.contrib.messages.add_message")
    def test_menuitem_move_node_permission_denied_if_not_latest_version(
        self, mocked_messages
    ):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=UNPUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=PUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=DRAFT)
        child = factories.ChildMenuItemFactory(parent=version.content.root)
        child_of_child = factories.ChildMenuItemFactory(parent=child)
        move_url = reverse(
            "admin:djangocms_navigation_menuitem_move_node", args=(version.content.id,)
        )
        data = {
            "node_id": child_of_child.pk,
            "sibling_id": version.content.root.pk,
            "as_child": 1,
        }

        response = self.client.post(move_url, data=data)

        # 400 error with error msg and node has not been moved
        self.assertEqual(response.status_code, 400)
        self.assertEqual(b"Version is not a draft", response.content)
        child.refresh_from_db()
        child_of_child.refresh_from_db()
        self.assertFalse(child_of_child.is_sibling_of(child))


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


class ListActionsTestCase(CMSTestCase):
    def setUp(self):
        self.modeladmin = admin.site._registry[MenuContent]

    def check_elements(self, elements, search_value, additional_search_value=None):
        """
        Finds a search term within a html tag sub element, returns True and element if hit.
        """
        additional_hit = True
        if additional_search_value:
            additional_hit = False
        for element in elements:
            for value in element.values():
                if search_value in value:
                    if additional_hit:
                        return True, element
                    else:
                        additional_hit = True

    def test_preview_link(self):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=UNPUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=PUBLISHED)
        menu_content = version.content
        func = self.modeladmin._list_actions(self.get_request("/admin"))

        response = func(menu_content)
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(response), parser)
        elements = tree.findall("//a")

        element_present, test_element = self.check_elements(elements, "cms-versioning-action-preview")

        self.assertTrue(element_present, "Missing a.cms-versioning-action-preview element")
        self.assertEqual(test_element.values()[0], "Preview")
        self.assertIn(reverse("admin:djangocms_navigation_menuitem_preview", args=(version.pk,),),
                      test_element.values()[2],
                      )

    def test_edit_link(self):
        menu = factories.MenuFactory()
        request = self.get_request("/")
        request.user = self.get_superuser()
        version = factories.MenuVersionFactory(content__menu=menu, state=DRAFT, created_by=request.user)
        func = self.modeladmin._list_actions(request)
        menu_content = version.content

        response = func(menu_content)
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(response), parser)
        elements = tree.findall("//a")

        element_present, test_element = self.check_elements(elements, "cms-versioning-action-btn", "Edit d")

        self.assertTrue(element_present, "Missing a.cms-versioning-action-btn Edit")
        self.assertEqual(test_element.values()[2], "Edit")

    def test_edit_link_inactive(self):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=DRAFT)
        request = self.get_request("/")
        func = self.modeladmin._list_actions(request)
        parser = etree.HTMLParser()
        response = func(version.content)

        tree = etree.parse(StringIO(response), parser)
        elements = tree.findall("//a")
        element_present, test_element = self.check_elements(elements, "cms-versioning-action-btn", "Edit")

        self.assertTrue(element_present, "Missing a.cms-versioning-action-edit element")
        self.assertIn("inactive", test_element.values()[0])
        self.assertEqual(test_element.values()[1], "Edit")
        self.assertNotIn("href", test_element.values())

    def test_edit_link_not_shown(self):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=UNPUBLISHED)
        func = self.modeladmin._list_actions(self.get_request("/"))

        response = func(version.content)
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(response), parser)
        element = tree.find("//a")
        element = "cms-versioning-action-edit" in element.values()

        self.assertFalse(
            element, "Element a.cms-versioning-action-edit is shown when it shouldn't"
        )

