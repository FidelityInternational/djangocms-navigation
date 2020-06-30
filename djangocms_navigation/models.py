from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import models
from django.shortcuts import reverse
from django.utils.translation import ugettext_lazy as _

from cms.models import CMSPlugin
from cms.utils.i18n import get_default_language

from treebeard.mp_tree import MP_Node

from .constants import TARGETS, TEMPLATE_DEFAULT, get_templates


__all__ = ["Menu", "MenuContent", "MenuItem", "NavigationPlugin"]


class AbstractMenu(models.Model):
    """
    MenuContent Grouper
    """
    site = models.ForeignKey(Site, related_name="%(app_label)s_%(class)s_site",
                             on_delete=models.PROTECT)
    identifier = models.CharField(verbose_name=_("identifier"), max_length=100)

    class Meta:
        abstract = True
        unique_together = (("identifier", "site"),)

    def __str__(self):
        return self.identifier

    @property
    def root_id(self):
        """Returns the id of the root MenuItem as it will be in the
        NavigationNode instance"""
        return "root-" + self.identifier


class AbstractMenuContent(models.Model):
    # There is an additional migration (0008_language_migration) to handle existing unpopulated database entries
    language = models.CharField(_("language"), max_length=15, db_index=True)

    class Meta:
        abstract = True


class AbstractMenuItem(MP_Node):
    title = models.CharField(verbose_name=_("title"), max_length=100)
    link_target = models.CharField(choices=TARGETS, default="_self", max_length=20)
    # Allow null for content as the root menu item won't have a link
    content_type = models.ForeignKey(
        ContentType, related_name="%(app_label)s_%(class)s_content_type",
        on_delete=models.PROTECT, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content = GenericForeignKey("content_type", "object_id")

    def __str__(self):
        return self.title

    class Meta:
        abstract = True


class Menu(AbstractMenu):
    pass


class MenuContent(AbstractMenuContent):
    menu = models.ForeignKey(Menu, on_delete=models.PROTECT)
    root = models.OneToOneField(
        "djangocms_navigation.MenuItem", on_delete=models.PROTECT
    )

    def __str__(self):
        return self.title

    @property
    def title(self):
        return self.root.title

    def get_preview_url(self):
        return reverse(
            "admin:{app}_{model}_preview".format(
                app=MenuItem._meta.app_label, model=MenuItem._meta.model_name
            ),
            args=[self.id],
        )


class MenuItem(AbstractMenuItem):
    pass


class NavigationPlugin(CMSPlugin):
    template = models.CharField(
        verbose_name=_("Template"),
        choices=get_templates(),
        default=TEMPLATE_DEFAULT,
        max_length=255,
    )
    menu = models.ForeignKey(Menu, on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("navigation plugin model")
        verbose_name_plural = _("navigation plugin models")

    def __str__(self):
        return self.get_template_display()
