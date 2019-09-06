from django.conf import settings
from django.utils.translation import ugettext_lazy as _

TARGETS = (
    ("_blank", _("Load in a new window")),
    ("_self", _("Load in the same frame as it was clicked")),
    ("_top", _("Load in the full body of the window")),
)
MENU_MODEL = 'MENU_MODEL'
ITEM_MODEL = 'ITEM_MODEL'


# Add additional choices through the ``settings.py``.
TEMPLATE_DEFAULT = getattr(
    settings, "DJANGOCMS_NAVIGATION_DEFAULT_TEMPLATE", "menu/menu.html"
)


def get_templates():
    choices = [(TEMPLATE_DEFAULT, _("Default"))]
    choices += getattr(settings, "DJANGOCMS_NAVIGATION_TEMPLATES", [])
    return choices
