from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from .utils import get_model

TARGETS = (
    ("_blank", _("Load in a new window")),
    ("_self", _("Load in the same frame as it was clicked")),
    ("_top", _("Load in the full body of the window")),
)


# Add additional choices through the ``settings.py``.
TEMPLATE_DEFAULT = getattr(
    settings, "DJANGOCMS_NAVIGATION_DEFAULT_TEMPLATE", "menu/menu.html"
)


def get_templates():
    choices = [(TEMPLATE_DEFAULT, _("Default"))]
    choices += getattr(settings, "DJANGOCMS_NAVIGATION_TEMPLATES", [])
    return choices


def get_select2_url_name():
    MenuContent = get_model('MENU_MODEL')
    url_name = "{}_select2_content_object".format(
        MenuContent._meta.app_label
    )
    return url_name
