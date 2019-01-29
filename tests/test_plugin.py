from mock import patch

from django.conf import settings
from django.contrib.auth.models import Permission

from cms.models import Page, CMSPlugin
from cms.plugin_pool import plugin_pool
from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.constants import PUBLISHED, DRAFT

from djangocms_navigation.test_utils import factories


class NavigationPluginTestCase(CMSTestCase):

    def setUp(self):
        plugin_pool._clear_cached()
        self.language = settings.LANGUAGES[0][0]
        self.superuser = self.get_superuser()
        plugin_permissions = Permission.objects.filter(
            content_type__model='cmsplugin')
        self.superuser.user_permissions.add(*plugin_permissions)
        plugin_permissions = Permission.objects.filter(
            content_type__model='navigationplugin')
        self.superuser.user_permissions.add(*plugin_permissions)

        self._login_context = self.login_user_context(self.superuser)
        self._login_context.__enter__()

    def _create_nav_plugin_on_page(self, placeholder):
        add_url = self.get_add_plugin_uri(
            placeholder=placeholder,
            plugin_type='Navigation',
            language=self.language,
        )
        data = {'template': 'menu/menu.html'}
        response = self.client.post(add_url, data)
        self.assertEqual(response.status_code, 200)
        return CMSPlugin.objects.latest('pk')

    def _edit_nav_plugin(self, plugin, template):
        endpoint = self.get_change_plugin_uri(plugin)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        data = {'template': template}
        response = self.client.post(endpoint, data)
        self.assertEqual(response.status_code, 200)
        return CMSPlugin.objects.get(pk=plugin.pk).get_bound_plugin()

    def test_can_add_edit_a_navigation_plugin(self):
        # NOTE: This test is based on:
        # https://github.com/divio/django-cms/blob/2daeb7d63cb5fee49575a834d0f23669ce46144e/cms/tests/test_plugins.py#L160

        # Set up a page with a published content version and one placeholder
        page_content = factories.PageContentWithVersionFactory(language=self.language)
        placeholder = factories.PlaceholderFactory(source=page_content)

        from djangocms_navigation.models import NavigationPlugin
        template_field = [f for f in NavigationPlugin._meta.fields if f.name == 'template'][0]
        with patch.object(template_field, 'choices', [('menu/menu.html', 'Default'), ('menu/menuismo.html', 'ismo')]):

            # Now create a plugin
            created_plugin = self._create_nav_plugin_on_page(placeholder)
            # Now edit the plugin
            plugin = self._edit_nav_plugin(created_plugin, "menu/menuismo.html")
            self.assertEqual("menu/menuismo.html", plugin.template)
    
