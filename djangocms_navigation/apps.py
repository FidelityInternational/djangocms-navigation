from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class NavigationConfig(AppConfig):
    name = "djangocms_navigation"
    verbose_name = _("django CMS Navigation")
