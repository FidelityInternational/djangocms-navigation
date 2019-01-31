from mock import patch

from django.conf import settings
from django.test import TestCase, RequestFactory

from cms.models import Page
from cms.test_utils.testcases import CMSTestCase
from menus.base import NavigationNode

from djangocms_navigation.cms_menus import NavigationSelector
from djangocms_navigation.models import NavigationPlugin
from djangocms_navigation.test_utils import factories

from .utils import disable_versioning_for_navigation


class NavigationSelectorTestCase(TestCase):

    def test_modify(self):
        selector = NavigationSelector(None)
        request = RequestFactory().get('/')
        nodes = [
            NavigationNode(
                title='',
                url='',
                id='root-fruit',
                parent_id=None,
                attr={},
            ),
            NavigationNode(
                title='',
                url='',
                id='root-vegetables',
                parent_id=None,
                attr={},
            ),
            NavigationNode(
                title='Apples',
                url='/fruit/apples/',
                id=26,
                parent_id='root-fruit',
                attr={'link_target': '_self'},
            ),
            NavigationNode(
                title='Celery',
                url='/vegetables/celery/',
                id=28,
                parent_id='root-vegetables',
                attr={'link_target': '_self'},
            ),
        ]
        namespace = None
        root_id = None
        post_cut = False
        breadcrumb = False
        result = selector.modify(request, nodes, namespace, root_id, post_cut, breadcrumb)
        #~ import ipdb; ipdb.set_trace()


class NavigationPluginViewTestCase(CMSTestCase):

    def setUp(self):
        self.language = settings.LANGUAGES[0][0]
        self.client.force_login(self.get_superuser())

    def test_can_add_edit_a_navigation_plugin_when_versioning_enabled(self):
        """Adds a navigation plugin with an http call and then
        edits the plugin with another http call."""
        # NOTE: This test is based on a similar one from django-cms:
        # https://github.com/divio/django-cms/blob/2daeb7d63cb5fee49575a834d0f23669ce46144e/cms/tests/test_plugins.py#L160

        # Set up a versioned page with one placeholder
        page_content = factories.PageContentWithVersionFactory(language=self.language)
        placeholder = factories.PlaceholderFactory(source=page_content)
        menu1 = factories.MenuContentWithVersionFactory().menu
        menu2 = factories.MenuContentWithVersionFactory().menu

        # Patch the choices on the template field, so we don't get
        # form validation errors
        template_field = [
            field for field in NavigationPlugin._meta.fields
            if field.name == 'template'
        ][0]
        patched_choices = [
            ('menu/menu.html', 'Default'),
            ('menu/menuismo.html', 'Menuismo')
        ]
        with patch.object(template_field, 'choices', patched_choices):

            # Start by testing the add view
            add_url = self.get_add_plugin_uri(
                placeholder=placeholder,
                plugin_type='Navigation',
                language=self.language,
            )
            # First do a GET on the add view
            response = self.client.get(add_url)
            self.assertEqual(response.status_code, 200)
            # Now do a POST call on the add view
            data = {'template': 'menu/menu.html', 'menu': menu1.pk}
            response = self.client.post(add_url, data)
            self.assertEqual(response.status_code, 200)
            created_plugin = NavigationPlugin.objects.latest('pk')
            self.assertEqual(created_plugin.template, 'menu/menu.html')
            self.assertEqual(created_plugin.menu, menu1)

            # Now that a plugin has been successfully created, try to edit it
            change_url = self.get_change_plugin_uri(created_plugin)
            # Start with a GET call on the change view
            response = self.client.get(change_url)
            self.assertEqual(response.status_code, 200)
            # Now do a POST call on the change view
            data = {'template': 'menu/menuismo.html', 'menu': menu2.pk}
            response = self.client.post(change_url, data)
            self.assertEqual(response.status_code, 200)
            plugin = NavigationPlugin.objects.get(
                pk=created_plugin.pk).get_bound_plugin()
            self.assertEqual(plugin.template, "menu/menuismo.html")
            self.assertEqual(plugin.menu, menu2)

            # publish
            version = page_content.versions.get()
            version.publish(self.get_superuser())

            # Go to the page
            page_url = page_content.page.get_absolute_url()
            response = self.client.get(page_url)
            self.assertEqual(response.status_code, 200)

    @disable_versioning_for_navigation()
    def test_can_add_edit_a_navigation_plugin_when_versioning_disabled(self):
        """Same test as above but with versioning disabled"""

        # Set up a versioned page (only disabling versioning for navigation)
        # with one placeholder
        page_content = factories.PageContentWithVersionFactory(language=self.language)
        placeholder = factories.PlaceholderFactory(source=page_content)
        menu1 = factories.MenuContentFactory().menu
        menu2 = factories.MenuContentFactory().menu

        # Patch the choices on the template field, so we don't get
        # form validation errors
        template_field = [
            field for field in NavigationPlugin._meta.fields
            if field.name == 'template'
        ][0]
        patched_choices = [
            ('menu/menu.html', 'Default'),
            ('menu/menuismo.html', 'Menuismo')
        ]
        with patch.object(template_field, 'choices', patched_choices):

            # Start by testing the add view
            add_url = self.get_add_plugin_uri(
                placeholder=placeholder,
                plugin_type='Navigation',
                language=self.language,
            )
            # First do a GET on the add view
            response = self.client.get(add_url)
            self.assertEqual(response.status_code, 200)
            # Now do a POST call on the add view
            data = {'template': 'menu/menu.html', 'menu': menu1.pk}
            response = self.client.post(add_url, data)
            self.assertEqual(response.status_code, 200)
            created_plugin = NavigationPlugin.objects.latest('pk')
            self.assertEqual(created_plugin.template, 'menu/menu.html')
            self.assertEqual(created_plugin.menu, menu1)

            # Now that a plugin has been successfully created, try to edit it
            change_url = self.get_change_plugin_uri(created_plugin)
            # Start with a GET call on the change view
            response = self.client.get(change_url)
            self.assertEqual(response.status_code, 200)
            # Now do a POST call on the change view
            data = {'template': 'menu/menuismo.html', 'menu': menu2.pk}
            response = self.client.post(change_url, data)
            self.assertEqual(response.status_code, 200)
            plugin = NavigationPlugin.objects.get(
                pk=created_plugin.pk).get_bound_plugin()
            self.assertEqual(plugin.template, "menu/menuismo.html")
            self.assertEqual(plugin.menu, menu2)
