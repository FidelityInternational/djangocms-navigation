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
    menu = models.ForeignKey(Menu, on_delete=models.PROTECT)
    root = models.ForeignKey('djangocms_navigation.MenuItem')

    def __str__(self):
        return self.title

    @property
    def title(self):
        return self.root.title


class MenuItem(MP_Node):
    title = models.CharField(verbose_name=_("title"), max_length=100)
    link_target = models.CharField(
        choices=TARGETS, default="_self", max_length=20)
    # Allow null for content as the root menu item won't have a link
    content_type = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content = GenericForeignKey("content_type", "object_id")
    # Override path field from treebeard so it is not unique. We're adding
    # a unique_together constraint per each menu content object instead.
    # Versioning needs to be able to duplicate menu items and we can't
    # really do that if path is unique per whole menu item table.
    path = models.CharField(max_length=255, unique=False)

    class Meta:
        unique_together = ('path', 'menu_content')

    def __str__(self):
        return self.title + str(self.pk)

    def get_parent(self, update=False):
        """Overrides treebeard's implementation to account for our
        meddlings with unique constraints on the path field.
        """
        depth = int(len(self.path) / self.steplen)
        if depth <= 1:
            return
        try:
            if update:
                del self._cached_parent_obj
            else:
                return self._cached_parent_obj
        except AttributeError:
            pass
        parentpath = self._get_basepath(self.path, depth - 1)
        # This get needs to be aware of menu_content as path is not unique
        self._cached_parent_obj = MenuItem.objects.get(
            path=parentpath, menu_content=self.menu_content)
        return self._cached_parent_obj


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
