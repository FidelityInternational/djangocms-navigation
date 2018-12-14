from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import ugettext_lazy as _

from cms.models import CMSPlugin

from treebeard.mp_tree import MP_Node

from .constants import TARGETS, TEMPLATE_DEFAULT, get_templates


__all__ = ["Menu", "MenuContent", "MenuItem", "NavigationPlugin"]


class Menu(models.Model):
    """
    MenuContent Grouper
    """

    identifier = models.CharField(verbose_name=_("identifier"), max_length=100)
    site = models.ForeignKey(Site, on_delete=models.PROTECT)

    class Meta:
        unique_together = (("identifier", "site"),)


class MenuContent(models.Model):
    title = models.CharField(verbose_name=_("title"), max_length=100)
    menu = models.ForeignKey(Menu, on_delete=models.PROTECT)

    def __str__(self):
        return self.title


class MenuItem(MP_Node):
    title = models.CharField(verbose_name=_("title"), max_length=100)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content = GenericForeignKey("content_type", "object_id")
    menu_content = models.ForeignKey(MenuContent, on_delete=models.PROTECT)
    link_target = models.CharField(choices=TARGETS, default="_self", max_length=20)

    def __str__(self):
        return self.title


class NavigationPlugin(CMSPlugin):
    template = models.CharField(
        verbose_name=_("Template"),
        choices=get_templates(),
        default=TEMPLATE_DEFAULT,
        max_length=255,
    )

    class Meta:
        verbose_name = _("navigation plugin model")
        verbose_name_plural = _("navigation plugin models")

    def __str__(self):
        return self.get_template_display()
