from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .forms import NavigationPluginForm
from .models import NavigationPlugin


__all__ = ["Navigation"]


@plugin_pool.register_plugin
class Navigation(CMSPluginBase):
    name = _("Navigation")
    model = NavigationPlugin
    form = NavigationPluginForm
    render_template = "djangocms_navigation/plugins/navigation.html"
