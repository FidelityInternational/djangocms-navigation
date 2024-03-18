import html
import importlib
import json
import sys
from unittest import skipIf, skipUnless
from unittest.mock import patch

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.contrib.sites.models import Site
from django.shortcuts import reverse
from django.test import RequestFactory
from django.test.utils import override_settings
from django.utils.translation import gettext_lazy as _

from cms.api import add_plugin, create_page, create_title
from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.utils import get_object_preview_url
from cms.utils.compat import DJANGO_4_1

from bs4 import BeautifulSoup
from djangocms_versioning.constants import DRAFT, PUBLISHED, UNPUBLISHED
from djangocms_versioning.exceptions import ConditionFailed
from djangocms_versioning.helpers import version_list_url

from djangocms_navigation import admin as nav_admin
from djangocms_navigation.admin import (
    MenuContentAdmin,
    MenuItemAdmin,
    MenuItemChangeList,
)
from djangocms_navigation.compat import TREEBEARD_4_5
from djangocms_navigation.models import Menu, MenuContent, MenuItem
from djangocms_navigation.test_utils import factories

from .utils import UsefulAssertsMixin, disable_versioning_for_navigation


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
        if not DJANGO_4_1:
            search_help_text = model_admin.search_help_text
            args.append(search_help_text)

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

    @patch('djangocms_navigation.conf.TREE_MAX_RESULT_PER_PAGE_COUNT', 11)
    def test_menuitem_changelist_pagination_setting_override(self):
        """
        The pagination should be driven by the setting:
        DJANGOCMS_NAVIGATION_TREE_MAX_RESULT_PER_PAGE_COUNT
        """
        # Remove the admin and then reload it which will reregister the models and the setting changes
        admin.site.unregister(MenuItem)
        admin.site.unregister(MenuContent)
        importlib.reload(nav_admin)

        admin_changelist = admin.site._registry[MenuItem]

        self.assertEqual(admin_changelist.list_per_page, 11)

    def test_menuitem_changelist_pagination_setting_default(self):
        """
        By default the pagination should be a higher than the django default of 100
        """
        admin_changelist = admin.site._registry[MenuItem]

        self.assertEqual(admin_changelist.list_per_page, sys.maxsize)


class MenuContentAdminViewTestCase(CMSTestCase):
    def setUp(self):
        self.client.force_login(self.get_superuser())
        self.admin_site = admin.AdminSite()
        self.admin_site.register(MenuContent, MenuContentAdmin)

    def test_menucontent_add_view(self):
        add_url = reverse("admin:djangocms_navigation_menucontent_add")

        response = self.client.post(add_url, {"title": "My Title", "language": "en"})

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

    @patch('djangocms_navigation.admin.using_version_lock', False)
    def test_list_display_without_version_locking(self):
        request = self.get_request("/")
        request.user = self.get_superuser()
        nav_admin.using_version_lock = False
        site_2 = Site.objects.create(domain="site_2.com", name="site_2")
        menu_1 = factories.MenuFactory(site=site_2)
        site_2_menu_version = factories.MenuVersionFactory(content__menu=menu_1, state=PUBLISHED)

        menu_content_admin = nav_admin.MenuContentAdmin(MenuContent, admin.AdminSite())
        func = menu_content_admin._list_actions(request)
        list_display_icons = func(site_2_menu_version.content)
        list_display = menu_content_admin.get_list_display(request)
        list_display[-1] = list_display_icons

        self.assertEqual(len(list_display), 5)
        self.assertEqual(
            list_display[0:4],
            ["title", "get_author", "get_modified_date", "get_versioning_state"]
        )
        self.assertIn("cms-versioning-action-btn", list_display[-1])
        # The preview button is present
        self.assertIn("cms-versioning-action-preview", list_display[-1])
        # The edit button is present
        self.assertIn("cms-versioning-action-edit", list_display[-1])
        self.assertIn("cms-form-get-method", list_display[-1])
        self.assertIn("js-versioning-action", list_display[-1])
        self.assertIn("js-versioning-keep-sideframe", list_display[-1])

    @override_settings(DJANGOCMS_NAVIGATION_VERSIONING_ENABLED=False)
    @disable_versioning_for_navigation()
    def test_list_display_without_versioning(self):
        request = self.get_request("/")
        request.user = self.get_superuser()

        menu_content_admin = MenuContentAdmin(MenuContent, admin.AdminSite())

        self.assertEqual(len(menu_content_admin.get_list_display(request)), 3)
        self.assertEqual(
            menu_content_admin.get_list_display(request), ["title", "get_menuitem_link", "get_preview_link"]
        )

    @override_settings(DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED=True)
    @patch('djangocms_navigation.admin.using_version_lock', False)
    @disable_versioning_for_navigation()
    def test_list_display_with_main_navigation(self):
        request = self.get_request("/")
        request.user = self.get_superuser()

        menu_content_admin = MenuContentAdmin(MenuContent, admin.AdminSite())

        self.assertEqual(len(menu_content_admin.get_list_display(request)), 4)
        self.assertEqual(
            menu_content_admin.get_list_display(request),
            ['title', 'get_main_navigation', 'get_menuitem_link', 'get_preview_link']
        )

    @override_settings(DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED=False)
    def test_get_list_actions_main_navigation_disabled(self):
        """
        When DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED is False, the actions should not contain the main navigation
        link
        """
        menu_content_admin = MenuContentAdmin(MenuContent, admin.AdminSite())
        actions = menu_content_admin.get_list_actions()

        self.assertNotIn(menu_content_admin._get_main_navigation_link, actions)

    @override_settings(DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED=True)
    def test_get_list_actions_main_navigation_enabled(self):
        """
        When DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED is True, the actions should contain the main navigation link
        """
        menu_content_admin = MenuContentAdmin(MenuContent, admin.AdminSite())
        actions = menu_content_admin.get_list_actions()

        self.assertIn(menu_content_admin._get_main_navigation_link, actions)


class MenuItemModelAdminTestCase(CMSTestCase):
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

        self.assertQuerySetEqual(
            queryset, [menu_contents[0].root.pk, child_item.pk], lambda o: o.pk
        )

    def test_get_list_display_for_preview_url(self):
        """
        The list actions should not be included in the list display for a preview url
        """
        request = self.get_request("/admin/djangocms_navigation/menuitem/1/preview/")
        request.user = self.get_superuser()

        self.assertEqual(len(self.model_admin.get_list_display(request)), 4)
        self.assertEqual(
            self.model_admin.get_list_display(request),
            ['__str__', 'get_object_url', 'soft_root', 'hide_node']
        )

    def test_get_list_display(self):
        """
        The list actions should be included when not a preview url
        """
        request = self.get_request("/admin/djangocms_navigation/menuitem/1/")
        request.user = self.get_superuser()

        # patch the _list_actions call to return something we can assert against
        with patch.object(self.model_admin, "_list_actions") as mock_list_actions:
            mock_list_actions.return_value = "list_actions"
            list_display = self.model_admin.get_list_display(request)

        mock_list_actions.assert_called_once_with(request)
        self.assertEqual(len(list_display), 5)
        self.assertEqual(
            list_display,
            ['__str__', 'get_object_url', 'soft_root', 'hide_node', "list_actions"]
        )

    @skipIf(TREEBEARD_4_5, "Test relevant only for treebeard>=4.6")
    def test_get_changelist_template_for_old_treebeard(self):
        """
        Check the template is the standard change list template when the request is for the changelist endpoint
        """
        request = self.get_request("/admin/djangocms_navigation/menuitem/1/")

        result = self.model_admin.get_changelist_template(request=request)

        self.assertEqual(result, "admin/djangocms_navigation/menuitem/tree_change_list.html")

    @skipUnless(TREEBEARD_4_5, "Test relevant only for treebeard<4.6")
    def test_get_changelist_template_for_new_treebeard(self):
        """
        Check the template is the standard change list template when the request is for the changelist endpoint
        """
        request = self.get_request("/admin/djangocms_navigation/menuitem/1/")

        result = self.model_admin.get_changelist_template(request=request)

        self.assertEqual(result, "admin/djangocms_navigation/menuitem/change_list.html")

    def test_get_changelist_template_preview(self):
        """
        Check the preview template is used when the request is for the preview endpoint
        """
        request = self.get_request("/admin/djangocms_navigation/menuitem/1/preview/")

        result = self.model_admin.get_changelist_template(request=request)

        self.assertEqual(result, "admin/djangocms_navigation/menuitem/preview.html")


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

        self.assertEqual(actual_message, expected_message)
        self.assertEqual(response.status_code, status_code)

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

        self.assertEqual(response.status_code, response_code)
        self.assertEqual(content, msg)

    @patch('djangocms_navigation.admin.using_version_lock', False)
    def test_moving_node_version_lock_not_installed_works_without_error(self):
        response = self.client.post(self.move_url, data=self.data)

        self.assertEqual(response.status_code, 200)
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
        self.assertRedirectsToVersionList(response, menu_content)
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
        self.assertRedirectsToVersionList(response, version.content)
        self.assertDjangoErrorMessage("Version is not a draft", mocked_messages)

    @patch("django.contrib.messages.error")
    def test_menuitem_change_view_redirects_if_not_latest_version_post(
        self, mocked_messages
    ):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, content__language="en", state=UNPUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, content__language="en", state=PUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, content__language="en", state=DRAFT)
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
        self.assertRedirectsToVersionList(response, version.content)
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
        self.assertRedirectsToVersionList(response, menu_content)
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
        self.assertRedirectsToVersionList(response, version.content)
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
        self.assertRedirectsToVersionList(response, version.content)
        self.assertDjangoErrorMessage("Version is not a draft", mocked_messages)
        # Menu item object was not added
        self.assertEqual(MenuItem.objects.filter(title="My new Title").count(), 0)

    def test_menuitem_changelist_should_have_get_url_column(self):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=PUBLISHED)
        mock_request = RequestFactory().get(
            reverse(
                "admin:djangocms_navigation_menuitem_list", args=(version.content.id,)
            )
        )
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
        self.assertEqual(len(ma.get_list_display(mock_request)), 5)
        self.assertIn("get_object_url", ma.get_list_display(mock_request))

    def test_menuitem_add_view_redirects_on_save_continue(self):
        """
        When a MenuIem object is created we check that the correct url is generated and redirected
        for the save and continue option and a message is shown to the user.
        """
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
            "_continue": ['Save and continue editing'],
        }

        response = self.client.post(add_url, data)
        new_child = MenuItem.objects.exclude(pk=menu_content.root.pk).get()

        self.assertEqual(
            response.url,
            reverse(
                "admin:djangocms_navigation_menuitem_change",
                kwargs={"menu_content_id": menu_content.pk, "object_id": new_child.id},
            )
        )

        response = self.client.post(add_url, data, follow=True)
        child = MenuItem.objects.exclude(pk__in=[menu_content.root.pk, new_child.id]).get()
        msg = _('Menuitem %(menuitem)s was changed successfully. You can edit it below') % {'menuitem': child.id}

        self.assertContains(response, msg)

    def test_menuitem_add_view_redirects_on_save_add_another(self):
        """
        When a MenuIem object is created we check that the correct url is generated and redirected
        for the save and add another option and a message is shown to the user.
        """
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
            '_addanother': ['Save and add another'],
        }
        response = self.client.post(add_url, data, follow=True)
        new_child = MenuItem.objects.exclude(pk=menu_content.root.pk).get()
        msg = _('Menuitem %(menuitem)s was changed successfully.') % {'menuitem': new_child.id}

        self.assertContains(response, msg)

        response = self.client.post(add_url, data)
        self.assertEqual(
            response.url,
            reverse(
                "admin:djangocms_navigation_menuitem_add", args=(menu_content.id,)
            )
        )


class MenuItemAdminPreviewViewTestCase(CMSTestCase):

    def setUp(self):
        self.client.force_login(self.get_superuser())
        self.menu_content = factories.MenuContentWithVersionFactory()
        factories.ChildMenuItemFactory.create_batch(5, parent=self.menu_content.root)
        self.preview_url = reverse(
            "admin:djangocms_navigation_menuitem_preview", args=(self.menu_content.id,)
        )

    def test_invalid_menucontent_id_raises_404(self):
        """
        Check that 404 response is returned if the menu_content_id is invalid
        """
        url = reverse("admin:djangocms_navigation_menuitem_preview", args=(999,))

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_add_item_link_not_present(self):
        """
        Check the button to add an item is not present
        """
        response = self.client.get(self.preview_url)
        add_url = reverse(
            "admin:djangocms_navigation_menuitem_add", args=(self.menu_content.id,)
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Add menu item")
        self.assertNotContains(response, add_url)

    def test_versions_link_not_present(self):
        """
        Check the button to view versions is not present
        """
        response = self.client.get(self.preview_url)
        version_url = version_list_url(self.menu_content)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Versions")
        self.assertNotContains(response, version_url)

    def test_actions_not_present(self):
        """
        Check that the Actions column is not present
        """
        response = self.client.get(self.preview_url)

        soup = BeautifulSoup(str(response.content), features="lxml")
        actions = soup.find(class_="column-list_actions")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Actions")
        self.assertIsNone(actions)

    def test_menuitem_preview_response_content(self):
        """
        Check that the response content only has the expected actions and buttons
        """
        response = self.client.get(self.preview_url)

        soup = BeautifulSoup(str(response.content), features="lxml")
        content_element = soup.find(id="content")
        title = content_element.find("h1").text
        buttons = content_element.find(class_="object-tools").find("li").find("a")
        changelist_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(self.menu_content.id,)
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(title, f"Preview Menu: {self.menu_content.title}")
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons["href"], changelist_url)

    def test_drag_drop_is_disabled(self):
        """
        Check that the drag/drop is disabled
        """
        response = self.client.get(self.preview_url)

        soup = BeautifulSoup(str(response.content), features="lxml")
        disable_drag_drop = soup.find(id="disable-drag-drop")

        self.assertEqual(disable_drag_drop["value"], "1")

    def test_menuitem_preview_check_for_expand_all(self):
        """
        Check that the expand / collapse all controls are present.
        """
        response = self.client.get(self.preview_url)

        soup = BeautifulSoup(str(response.content), features="lxml")
        element = soup.find("th", class_="expand-all")
        link = element.find("a")

        self.assertIsNotNone(element)
        self.assertEqual(_('Toggle expand/collapse all'), link['title'])
        self.assertIn('+', link.string)

    def test_menuitem_preview_context(self):
        """
        Check that the context contains the correct title and the menucontent object
        """
        model_admin = MenuItemAdmin(MenuItem, admin.AdminSite())
        request = self.get_request("/admin/djangocms_navigation/menuitem/1/preview/")
        request.user = self.get_superuser()
        menu_content = factories.MenuContentWithVersionFactory()

        response = model_admin.preview_view(request=request, menu_content_id=menu_content.pk)

        self.assertEqual(response.context_data["title"], f"Preview Menu: {menu_content.title}")
        self.assertEqual(response.context_data["menu_content"], menu_content)


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

        self.assertContains(response, version_list_url(menu_content))

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
        self.assertRedirectsToVersionList(response, menu_content)
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
        self.assertRedirectsToVersionList(response, version.content)
        self.assertDjangoErrorMessage("Version is not a draft", mocked_messages)

    def test_menuitem_changelist_validate_messages_endpoint(self):
        """
        The messages endpoint provides async code with access to the django message queue.
        Endpoint is required to fetch update messages after common treebeard operations
        (like moving a tree node) without reloading page.
        """
        menu_content = factories.MenuContentWithVersionFactory(version__created_by=self.get_superuser())
        child = factories.ChildMenuItemFactory(parent=menu_content.root)
        grandchild = factories.ChildMenuItemFactory(parent=child)
        data = {
            "node_id": grandchild.id,
            "sibling_id": menu_content.root.id,
            "as_child": 1,
        }
        move_endpoint = reverse(
            "admin:djangocms_navigation_menuitem_move_node", args=(menu_content.id,)
        )
        messages_endpoint = reverse(
            "admin:djangocms_navigation_menuitem_message_storage", args=(menu_content.id,)
        )
        move_response = self.client.post(move_endpoint, data)
        messages_response = self.client.get(messages_endpoint)

        # Check both calls come back successful:
        self.assertEqual(move_response.status_code, 200)
        self.assertEqual(messages_response.status_code, 200)

        # Check message result is as expected:
        msg = json.loads(messages_response.content)['messages'][0]
        self.assertEqual(msg['level'], 'info')
        self.assertIn('Moved node', msg['message'])

    def test_menuitem_changelist_default_tree_layout(self):
        """
        Parsing output from template tags to verify markup for default layout is present:
        Root node (level 1) is expanded, Child nodes / level 2 are collapsed,
        level 3 are display: none, and css spacer variable is present.
        """
        menu_content = factories.MenuContentWithVersionFactory()
        menu_items = factories.ChildMenuItemFactory.create_batch(3, parent=menu_content.root)
        for item in menu_items:
            factories.ChildMenuItemFactory.create_batch(2, parent=item)

        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )
        response = self.client.get(list_url)

        # Parse returned html for root and child nodes:
        soup = BeautifulSoup(str(response.content), features="lxml")
        root_node = soup.find("tr", level="1")  # root node is always level=1
        level_2_nodes = soup.find_all("tr", level="2")
        level_3_nodes = soup.find_all("tr", level="3")

        # Assert / verify default root and child node layouts (set in get_collapse tag):
        self.assertIsNotNone(root_node.find("a", class_="collapse expanded"))
        self.assertEqual(
            '--s-width:0',
            root_node.find("span", class_="spacer")['style']
        )
        self.assertNotIn(
            None,
            [node.find("a", class_="collapse collapsed") for node in level_2_nodes]
        )
        # Assert / verify level 3 nodes are display: none (set in html via result_tree tag):
        for node in level_3_nodes:
            self.assertEqual("display: none;", node['style'])

    def test_menuitem_changelist_custom_js(self):
        """
        Check that custom javascript for overriding treebeard js is present.
        """
        menu_content = factories.MenuContentWithVersionFactory()

        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )
        response = self.client.get(list_url)

        self.assertContains(
            response,
            'djangocms_navigation/js/navigation-tree-admin.js',
        )

    def test_menuitem_changelist_check_for_expand_all(self):
        """
        Check that the expand / collapse all controls are present.
        """
        menu_content = factories.MenuContentWithVersionFactory()

        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )
        response = self.client.get(list_url)

        soup = BeautifulSoup(str(response.content), features="lxml")
        element = soup.find("th", class_="expand-all")
        link = element.find("a")

        self.assertIsNotNone(element)
        self.assertEqual(_('Toggle expand/collapse all'), link['title'])
        self.assertIn('+', link.string)

    def test_menuitem_move_message(self):
        """
        Check that confirmation message displayed when moving a menu item is present on the page via a data attribute on
        the tbody element
        """
        menu_content = factories.MenuContentWithVersionFactory()

        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )
        response = self.client.get(list_url)

        soup = BeautifulSoup(str(response.content), features="lxml")
        element = soup.find("tbody")
        self.assertEqual(element.attrs["data-move-message"], "Are you sure you want to move menu item")

    def test_menu_content_id_present(self):
        """
        Check that the rendered template includes the menu content id as a data attribute so that it can be accessed by
        the client side js
        """
        menu_content = factories.MenuContentWithVersionFactory()
        list_url = reverse(
            "admin:djangocms_navigation_menuitem_list", args=(menu_content.id,)
        )
        response = self.client.get(list_url)

        soup = BeautifulSoup(str(response.content), features="lxml")
        result_list = soup.find(id="result_list")

        self.assertEqual(result_list["data-menu-content-id"], str(menu_content.pk))


@override_settings(
    CMS_PERMISSION=True,
    CMS_CAHCE_DURATIONS={
        'menus': 60,
        'content': 60,
        'permissions': 60,
    },
)
class MenuItemAdminDeleteViewTestCase(CMSTestCase):
    def setUp(self):
        self.user = self.get_superuser()
        self.client.force_login(self.user)

    def test_menuitem_delete_view_item_without_children(self):
        """
        Single MenuItem is shown in confirmation, and then deleted on second request
        """
        menu_content = factories.MenuContentWithVersionFactory(version__created_by=self.user)
        child = factories.ChildMenuItemFactory(parent=menu_content.root)

        # Get the url for deleting a single URL
        delete_url_single = reverse(
            "admin:djangocms_navigation_menuitem_delete", args=(menu_content.id, child.id,)
        )

        with self.login_user_context(self.user):
            # Hit the confirmation page using get request
            confirmation_response = self.client.get(
                delete_url_single, data={"menu_content_id": menu_content.id}
            )
            response = self.client.post(
                delete_url_single, follow=True, data={"menu_content_id": menu_content.id}
            )

        # check the context contains the expected structure of objects so that it is rendered correctly in the template
        expected_deleted_objects = [f"Menu item: {child}"]
        self.assertEqual(confirmation_response.context["deleted_objects"], expected_deleted_objects)
        # Confirmation screen populated with all to-be deleted items
        self.assertContains(
            confirmation_response,
            '<p>Are you sure you want to delete the menu item "{}"?'.format(child)
        )
        self.assertContains(
            confirmation_response,
            'All of the following related items will be deleted:</p>'
        )
        self.assertContains(
            confirmation_response,
            '<ul>\t<li>Menu item: {}</li></ul'.format(
                child
            )
        )
        # Confirm deletion was success
        self.assertContains(
            response,
            '<li class="success">The menu item “{}” was deleted successfully.</li>'.format(child),
        )
        self.assertEqual(MenuItem._base_manager.count(), 1)

    def test_menuitem_delete_view_item_with_children(self):
        """
        Multi MenuItem is shown in confirmation, and then deleted on second request
        """
        menu_content = factories.MenuContentWithVersionFactory(version__created_by=self.user)
        child = factories.ChildMenuItemFactory(parent=menu_content.root)
        child_of_child = factories.ChildMenuItemFactory(parent=child)
        child_of_child_of_child = factories.ChildMenuItemFactory(parent=child_of_child)
        # Delete an editable node, with children
        delete_url_with_child = reverse(
            "admin:djangocms_navigation_menuitem_delete", args=(menu_content.id, child.id,),
        )
        with self.login_user_context(self.user):
            # Hit the confirmation page using get
            confirmation_response = self.client.get(
                delete_url_with_child, data={"menu_content_id": menu_content.id}
            )
            response = self.client.post(
                delete_url_with_child, follow=True, data={"menu_content_id": menu_content.id}
            )

        # check the context contains the expected structure of objects so that it is rendered correctly in the template
        expected_deleted_objects = [
            f"Menu item: {child}",
            [
                f"Menu item: {child_of_child}",
                [
                    f"Menu item: {child_of_child_of_child}"
                ]
            ]
        ]
        self.assertEqual(confirmation_response.context_data["deleted_objects"], expected_deleted_objects)
        # Confirmation screen populated with all to be deleted items
        self.assertContains(
            confirmation_response,
            '<p>Are you sure you want to delete the menu item "{}"?'.format(child)
        )
        self.assertContains(
            confirmation_response,
            'All of the following related items will be deleted:</p>'
        )
        self.assertContains(
            confirmation_response,
            '<ul>\t<li>Menu item: {}\n\t'.format(
                child
            )
        )
        # two tabs indicate this item is nested under the previous node
        self.assertContains(
            confirmation_response,
            '<ul>\n\t\t<li>Menu item: {}\n\t\t'.format(
                child_of_child
            )
        )
        # three tabs indicates this item is nested under the previous child node
        # and then the previous <ul> elements are closed
        self.assertContains(
            confirmation_response,
            '<ul>\n\t\t\t<li>Menu item: {}</li>\n\t\t</ul>\n\t\t</li>\n\t</ul>\n\t</li></ul>'.format(
                child_of_child_of_child
            )
        )

        content = response.content.decode('utf-8')

        self.assertEqual(MenuItem._base_manager.count(), 1)
        self.assertIn(
            '<li class="success">The menu item “{}” was deleted successfully.</li>'.format(child),
            content
        )

    def test_menuitem_delete_view_with_permission(self):
        """
        With appropriate permissions, the delete view allows deletion of Menuitems
        """
        user_with_delete_permissions = self._create_user(
            "user_with_delete", is_staff=True
        )
        menu_content = factories.MenuContentWithVersionFactory(version__created_by=user_with_delete_permissions)
        child = factories.ChildMenuItemFactory(parent=menu_content.root)
        new_child = factories.ChildMenuItemFactory(parent=menu_content.root)
        child_of_child = factories.ChildMenuItemFactory(parent=child)
        factories.ChildMenuItemFactory(parent=child_of_child)

        self.add_permission(user_with_delete_permissions, "view_menucontentversion")
        self.add_permission(user_with_delete_permissions, "delete_menuitem")

        # Delete one, editable node, with no children
        delete_url_single = reverse(
            "admin:djangocms_navigation_menuitem_delete", args=(menu_content.id, new_child.id,)
        )
        with self.login_user_context(user_with_delete_permissions):
            # Hit the delete view using POST (i.e. confirmed delete)
            response = self.client.post(
                delete_url_single, follow=True, data={"menu_content_id": menu_content.id}
            )

        content = response.content.decode('utf-8')

        self.assertEqual(MenuItem._base_manager.count(), 4)
        self.assertIn(
            '<li class="success">The menu item “{}” was deleted successfully.</li>'.format(new_child),
            content
        )

    def test_menuitem_delete_view_without_permission(self):
        """
        User does not have appropriate permissions, redirect and provide error message
        """
        menu_content = factories.MenuContentWithVersionFactory(version__created_by=self.user)
        factories.ChildMenuItemFactory(parent=menu_content.root)
        new_child = factories.ChildMenuItemFactory(parent=menu_content.root)

        url = reverse(
            "admin:djangocms_navigation_menuitem_delete", args=(menu_content.id, new_child.id,)
        )
        user_without_delete_permissions = self._create_user(
            "user_without_delete", is_staff=True
        )
        self.add_permission(user_without_delete_permissions, "view_menucontentversion")

        with self.login_user_context(user=user_without_delete_permissions):
            response = self.client.post(url, follow=True)
        content = response.content.decode('utf-8')
        content = html.unescape(content)

        self.assertIn(
            '''<li class="error">The item is currently locked or you don\'t have permission to change it</li>''',
            content
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MenuItem._base_manager.count(), 3)

    def test_menuitem_delete_view_root(self):
        """
        Root cannot be deleted, user is redirected without deletion
        """
        menu_content = factories.MenuContentWithVersionFactory(version__created_by=self.user)

        url = reverse(
            "admin:djangocms_navigation_menuitem_delete", args=(menu_content.id, menu_content.root.id)
        )
        with self.login_user_context(user=self.user):
            response = self.client.post(url, follow=True, data={"menu_content_id": menu_content.id})

        self.assertContains(
            response, '<li class="error">This item is the root of a menu, therefore it cannot be deleted.</li>'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MenuItem._base_manager.count(), 1)

    def test_menuitem_delete_view_breadcrumbs(self):
        """
        Breadcrumbs for the delete view should render valid url's
        """
        menu_content = factories.MenuContentWithVersionFactory(version__created_by=self.user)
        child = factories.ChildMenuItemFactory(parent=menu_content.root)

        # Get the url for deleting a single URL
        delete_url_single = reverse(
            "admin:djangocms_navigation_menuitem_delete", args=(menu_content.id, child.id,)
        )

        with self.login_user_context(self.user):
            # Hit the confirmation page using get request
            confirmation_response = self.client.get(
                delete_url_single, data={"menu_content_id": menu_content.id}
            )

        # Get all the hrefs in the markup for the breadcrumbs div
        soup = BeautifulSoup(confirmation_response.rendered_content, 'html.parser')
        breadcrumb_html = soup.find("div", class_="breadcrumbs")
        breadcrumb_url = []

        for a in breadcrumb_html.find_all('a', href=True):
            breadcrumb_url.append(a['href'])

        with self.login_user_context(self.user):
            breadcrumb_first = self.client.get(breadcrumb_url[0])
            self.assertContains(
                breadcrumb_first,
                "<h1>Site administration</h1>"
            )
            self.assertContains(
                breadcrumb_first,
                '<a href="/en/admin/djangocms_navigation/menucontent/" class="changelink">Change</a>'
            )
            breadcrumb_second = self.client.get(breadcrumb_url[1])
            self.assertContains(
                breadcrumb_second, "<h1>django CMS Navigation administration</h1>")
            self.assertContains(
                breadcrumb_second,
                '<a href="/en/admin/djangocms_navigation/menucontent/">Menu contents</a>'
            )
            breadcrumb_third = self.client.get(breadcrumb_url[2])
            self.assertContains(
                breadcrumb_third,
                "<h1>Edit Menu: %s</h1>" % menu_content.root
            )
            self.assertContains(
                breadcrumb_third,
                '<a href="/en/admin/djangocms_navigation/menuitem/1/1/change/">%s</a></th>' % menu_content.root)
            breadcrumb_fourth = self.client.get(breadcrumb_url[3])
            self.assertContains(
                breadcrumb_fourth,
                "<h1>Edit Menu: %s</h1>" % menu_content.root
            )
            self.assertContains(
                confirmation_response, '<li>Menu item: %s</li>' % child.title)
            self.assertContains(
                confirmation_response, '<p>Are you sure you want to delete the menu item "%s"? All of the following '
                                       'related items will be deleted:</p>' % child.title)


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


class MenuItemMainNavigationViewTestCase(CMSTestCase):
    @override_settings(DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED=True)
    @patch("djangocms_navigation.admin.purge_menu_cache")
    def test_make_main_navigation_view_with_existing_main_navigation(self, purge_menu_cache):
        """
        With a main navigation already set, change the provided to main, and unset the old main.
        """
        # Create a menucontent, with a menu that is already the main navigation
        original_menu_content = factories.MenuContentWithVersionFactory(language="en")
        original_menu = original_menu_content.menu
        original_menu.main_navigation = True
        original_menu.save()
        # Create another, without main_navigation set
        new_menu_content = factories.MenuContentWithVersionFactory(language="en")
        main_navigation_url = reverse(
            "admin:{app}_{model}_main_navigation".format(
                app=new_menu_content._meta.app_label, model=new_menu_content._meta.model_name,
            ),
            args=[new_menu_content.pk],
        )
        with self.login_user_context(self.get_superuser()):
            response = self.client.get(main_navigation_url)

        expected_identifier = new_menu_content.menu.identifier

        # the call the purge_menu_cache is patched so that we can assert it was not called before confirming the change
        purge_menu_cache.assert_not_called()
        # Verify that we have rendered the confirmation screen
        self.assertContains(
            response,
            (
                f"<h4>Are you sure you would like to set the menu: <u>{expected_identifier}</u>"
                " as the main navigation?</h4>"
            )
        )
        self.assertContains(
            response,
            "<h4>By doing this, the existing navigation below will no longer be the main navigation.</h4>"
        )
        self.assertContains(
            response, f"<p>{original_menu.identifier}</p>"
        )

        with self.login_user_context(self.get_superuser()):
            response = self.client.post(main_navigation_url, follow=True)

        self.assertContains(
            response,
            f'<li class="info">You have set the navigation {expected_identifier} as the main navigation.</li>'
        )

        # the call the purge_menu_cache is patched so that we can assert that it was called after confirming change
        purge_menu_cache.assert_called_once_with(site_id=new_menu_content.menu.site.id)
        # Refresh from db, since these instances won't have updated.
        original_menu.refresh_from_db()
        new_menu_content.refresh_from_db()

        self.assertEqual(original_menu.main_navigation, False)
        self.assertEqual(new_menu_content.menu.main_navigation, True)

    @override_settings(DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED=True)
    def test_make_main_navigation_view_without_existing_main_navigation(self):
        """
        With no other main navigation, set the provided menucontent to the main navigation.
        """
        # Create a menucontent
        new_menu_content = factories.MenuContentWithVersionFactory(language="en")
        main_navigation_url = reverse(
            "admin:{app}_{model}_main_navigation".format(
                app=new_menu_content._meta.app_label, model=new_menu_content._meta.model_name,
            ),
            args=[new_menu_content.pk],
        )
        with self.login_user_context(self.get_superuser()):
            response = self.client.get(main_navigation_url)
        expected_identifier = new_menu_content.menu.identifier

        # Verify that we have rendered the confirmation screen
        self.assertContains(
            response,
            (
                f"<h4>Are you sure you would like to set the menu: <u>{expected_identifier}</u>"
                " as the main navigation?</h4>"
            )
        )
        # No need to warn users if there is no other main navigation
        self.assertNotContains(
            response,
            "<h4>By doing this, the existing main navigation below will no longer be the main navigation.</h4>"
        )

        with self.login_user_context(self.get_superuser()):
            response = self.client.post(main_navigation_url, follow=True)

        self.assertContains(
            response,
            f'<li class="info">You have set the navigation {expected_identifier} as the main navigation.</li>'
        )

        # Refresh from db as this instance won't have updated.
        new_menu_content.refresh_from_db()
        self.assertEqual(new_menu_content.menu.main_navigation, True)

    @override_settings(DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED=False)
    def test_make_navigation_view_throws_error_when_disabled(self):
        """
        With DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED set False, raise a 404 when the view is accessed.
        """
        menu_content = factories.MenuContentWithVersionFactory(language="en")
        main_navigation_url = reverse(
            "admin:{app}_{model}_main_navigation".format(
                app=menu_content._meta.app_label, model=menu_content._meta.model_name,
            ),
            args=[menu_content.pk],
        )

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(main_navigation_url)

        self.assertEqual(response.status_code, 404)

    @override_settings(DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED=True)
    def test_make_navigation_view_throws_error_invalid_menucontent(self):
        """
        With an invalid MenuContent ID, raise 404.
        """
        # Generate a main_navigation url with an invalid MenuContent ID
        main_navigation_url = reverse(
            "admin:{app}_{model}_main_navigation".format(
                app=MenuContent._meta.app_label, model=MenuContent._meta.model_name,
            ),
            args=[111],
        )

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(main_navigation_url)

        self.assertEqual(response.status_code, 404)


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


class MenuListActionsTestCase(CMSTestCase):
    def setUp(self):
        self.modeladmin = admin.site._registry[MenuContent]

    def test_preview_link(self):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=UNPUBLISHED)
        factories.MenuVersionFactory(content__menu=menu, state=PUBLISHED)
        menu_content = version.content

        preview_endpoint = reverse("admin:djangocms_navigation_menuitem_preview", args=(version.pk,),)
        func = self.modeladmin._list_actions(self.get_request("/admin"))
        response = func(menu_content)

        self.assertIn("cms-versioning-action-preview", response)
        self.assertIn('title="Preview"', response)
        self.assertIn(preview_endpoint, response)

    def test_edit_link(self):
        menu = factories.MenuFactory()
        request = self.get_request("/")
        request.user = self.get_superuser()
        version = factories.MenuVersionFactory(content__menu=menu, state=DRAFT, created_by=request.user)
        menu_content = version.content

        func = self.modeladmin._list_actions(request)
        edit_endpoint = reverse("admin:djangocms_versioning_menucontentversion_edit_redirect", args=(version.pk,),)
        response = func(menu_content)

        self.assertIn("cms-versioning-action-btn", response)
        self.assertIn('title="Edit"', response)
        self.assertIn(edit_endpoint, response)

    def test_edit_link_inactive(self):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=DRAFT)
        request = self.get_request("/")

        func = self.modeladmin._list_actions(request)
        edit_endpoint = reverse("admin:djangocms_versioning_menucontentversion_edit_redirect", args=(version.pk,),)
        response = func(version.content)

        self.assertIn("inactive", response)
        self.assertIn('title="Edit"', response)
        self.assertNotIn(edit_endpoint, response)

    def test_edit_link_not_shown(self):
        menu = factories.MenuFactory()
        version = factories.MenuVersionFactory(content__menu=menu, state=UNPUBLISHED)
        func = self.modeladmin._list_actions(self.get_request("/"))

        response = func(version.content)

        self.assertNotIn("cms-versioning-action-edit ", response)


class MenuItemListActionsTestCase(CMSTestCase):
    def setUp(self):
        self.modeladmin = admin.site._registry[MenuItem]

    def test_edit_link(self):
        user = self.get_superuser()
        menu_content = factories.MenuContentWithVersionFactory(version__created_by=user)
        request = self.get_request("/")
        request.user = self.get_superuser()
        request.menu_content_id = menu_content.pk

        func = self.modeladmin._list_actions(request)
        edit_endpoint = reverse(
            "admin:djangocms_navigation_menuitem_change", args=(menu_content.pk, menu_content.root.pk),
        )
        response = func(menu_content.root)

        self.assertIn("cms-versioning-action-btn", response)
        self.assertIn('title="Edit"', response)
        self.assertIn(edit_endpoint, response)


class ChangelistSideframeControlsTestCase(CMSTestCase):
    def setUp(self):
        self.menucontent_modeladmin = admin.site._registry[MenuContent]
        self.menuitem_modeladmin = admin.site._registry[MenuItem]

    def test_menucontent_changelist_url_link_opens_in_sideframe(self):
        """
        When clicking on the navigation menucontent edit, the sideframe is kept open
        """
        user = self.get_superuser()
        menucontent = factories.MenuContentWithVersionFactory(version__created_by=user)
        request = self.get_request("/")
        request.user = self.get_superuser()
        request.menu_content_id = menucontent.pk
        url_markup = self.menucontent_modeladmin._get_edit_link(menucontent, request)

        # The url link should keep the sideframe open
        self.assertIn("js-versioning-keep-sideframe", url_markup)
        self.assertNotIn("js-versioning-close-sideframe", url_markup)

    def test_menucontent_preview_link_opens_in_sideframe(self):
        """
        When clicking on the navigation menucontent preview, the sideframe is kept open
        """
        user = self.get_superuser()
        menucontent = factories.MenuContentWithVersionFactory(version__created_by=user)
        request = self.get_request("/")
        request.user = self.get_superuser()
        request.menu_content_id = menucontent.pk
        url_markup = self.menucontent_modeladmin._get_preview_link(menucontent, request)

        # The url link should keep the sideframe open
        self.assertIn("js-versioning-keep-sideframe", url_markup)
        self.assertNotIn("js-versioning-close-sideframe", url_markup)

    def test_menuitem_changelist_edit_url_link_opens_in_sideframe(self):
        """
        When clicking on the navigation menuitem edit, the sideframe is kept open
        """
        user = self.get_superuser()
        menucontent = factories.MenuContentWithVersionFactory(version__created_by=user)
        child = factories.ChildMenuItemFactory(parent=menucontent.root)

        request = self.get_request("/")
        request.user = self.get_superuser()
        request.menu_content_id = menucontent.pk
        url_markup = self.menuitem_modeladmin._get_edit_link(child, request)

        # The url link should keep the sideframe open
        self.assertIn("js-versioning-keep-sideframe", url_markup)
        self.assertNotIn("js-versioning-close-sideframe", url_markup)

    def test_menuitem_changelist_delete_url_link_opens_in_sideframe(self):
        """
        When clicking on the navigation menuitem edit, the sideframe is kept open
        """
        user = self.get_superuser()
        menucontent = factories.MenuContentWithVersionFactory(version__created_by=user)
        child = factories.ChildMenuItemFactory(parent=menucontent.root)

        request = self.get_request("/")
        request.user = self.get_superuser()
        request.menu_content_id = menucontent.pk
        url_markup = self.menuitem_modeladmin._get_delete_link(child, request)

        # The url link should keep the sideframe open
        self.assertIn("js-versioning-keep-sideframe", url_markup)
        self.assertNotIn("js-versioning-close-sideframe", url_markup)


class ReferencesIntegrationTestCase(CMSTestCase):

    def setUp(self):
        self.user = self.get_superuser()

    def test_menucontent_references_integration(self):
        """
        When opening the references for a given navigation menu, the objects which reference it should be listed
        """
        menucontent = factories.MenuContentWithVersionFactory(version__created_by=self.user)
        kwargs = {"created_by": self.user}
        page = create_page(
            title="Navigation Integration Page",
            template="page.html",
            language="en",
            menu_title="",
            in_navigation=True,
            **kwargs
        )
        page_content = create_title("en", "Draft Page", page, created_by=self.user)

        placeholder = factories.PlaceholderFactory(
            source=page_content,
        )
        menu = menucontent.menu
        navigation_plugin = add_plugin(
            placeholder,
            "Navigation",
            language="en",
            template="default",
            menu=menu,
        )

        navigation_content_type = ContentType.objects.get(app_label="djangocms_navigation", model="menu")
        references_endpoint = reverse(
            "djangocms_references:references-index",
            kwargs={"content_type_id": navigation_content_type.id, "object_id": menu.id}
        )

        with self.login_user_context(self.user):
            response = self.client.get(references_endpoint)

        self.assertContains(response, navigation_plugin.menu.__str__())
        self.assertContains(response, "menu")
        self.assertContains(response, navigation_plugin.plugin_type.lower())
        self.assertContains(response, get_object_preview_url(page_content))
