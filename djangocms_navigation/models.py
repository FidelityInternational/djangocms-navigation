from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import ugettext_lazy as _
from treebeard.mp_tree import MP_Node

TARGETS = (
    ('_blank', _('Load in a new window')),
    ('_self', _('Load in the same frame as it was clicked')),
    ('_top', _('Load in the full body of the window')),
)


class Menu(models.Model):
    """
    MenuContent Grouper
    """
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
    )


class MenuContent(models.Model):
    title = models.CharField(
        verbose_name=_('title'),
        max_length=100
    )
    menu = models.ForeignKey(
        Menu,
        on_delete=models.PROTECT,
    )

    def __str__(self):
        return self.title


class MenuItem(MP_Node):
    title = models.CharField(
        verbose_name=_('title'),
        max_length=100
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
    )
    object_id = models.PositiveIntegerField()
    content = GenericForeignKey('content_type', 'object_id')
    menu_content = models.ForeignKey(
        MenuContent, on_delete=models.PROTECT,
    )
    link_target = models.CharField(
        choices=TARGETS,
        default='_self',
        max_length=20,
    )

    def __str__(self):
        return self.title
