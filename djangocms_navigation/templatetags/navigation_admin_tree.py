# -*- coding: utf-8 -*-
from django import template
from django.contrib.admin.templatetags.admin_list import (
    result_headers,
    result_hidden_fields,
)
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from treebeard.templatetags import admin_tree, needs_checkboxes
from treebeard.templatetags.admin_tree import check_empty_dict, results

from djangocms_navigation.helpers import is_preview_url


register = template.Library()

"""
This module is simply for overwriting some of treebeard's admin_tree templatetag functions
with djangocms_navigation specific values.

CAVEAT: Treebeard encapulates markup in some of it's template tags, so we are needing
to keep the same approach in order to overwrite markup, ie. with get_space and get_collapse below.
"""


def get_spacer(first, result):
    if first:
        spacer = f'<span class="spacer" style="--s-width:{(result.get_depth() - 1)}">&nbsp;</span>'
    else:
        spacer = ''

    return spacer


admin_tree.get_spacer = get_spacer


def get_collapse(result):
    if result.get_children_count():
        # Show only the first level navigation, collapse sub-levels by default:
        if result.get_depth() > 1:
            collapse = ('<a href="#" title="" class="collapse collapsed">'
                        '-</a>')
        else:
            collapse = ('<a href="#" title="" class="collapse expanded">'
                        '-</a>')
    else:
        collapse = '<span class="collapse">&nbsp;</span>'

    return collapse


admin_tree.get_collapse = get_collapse


@admin_tree.register.inclusion_tag(
    'djangocms_navigation/admin/tree_change_list_results.html', takes_context=True)
def result_tree(context, cl, request):

    headers = list(result_headers(cl))
    headers.insert(1 if needs_checkboxes(context) else 0, {
        'text': '+',
        'sortable': True,
        'url': request.path,
        'tooltip': _('Toggle expand/collapse all'),
        'class_attrib': mark_safe(' class="expand-all"')
    })

    # if this is the preview view, we still want the collapsible navigation to be usable, but the drag drop feature
    # should be disabled as this the preview view is readonly
    disable_drag_drop = is_preview_url(request=request)

    # Message defined here so that it is translatable. The title of the menu item is appended to the message in the JS
    move_node_message = _("Are you sure you want to move menu item")

    # The ID is used when storing the menu tree state in the client session object, but as this templatetag can be used
    # outside of djangocms-navigation, check safely if a MenuContent object is in the current context object
    try:
        menu_content_id = context["menu_content"].pk
    except KeyError:
        menu_content_id = ""

    return {
        'filtered': not check_empty_dict(request.GET),
        'result_hidden_fields': list(result_hidden_fields(cl)),
        'result_headers': headers,
        'results': list(results(cl)),
        'disable_drag_drop': disable_drag_drop,
        'move_node_message': move_node_message,
        'menu_content_id': menu_content_id,
    }


@admin_tree.register.simple_tag
def treebeard_js():
    """
    CAVEAT: This is an replication and overwrite of treebeard_js tag in order to insert navigation specific js file.
            Because djangocms-navigation/change_list template still needs to inherit (block.super) in extrahead tag,
            in order to overwrite treebeard js, javascript script injection is being kept as a template tag
            instead of directly placed in template.
    """

    js_file = static('djangocms_navigation/js/navigation-tree-admin.js')
    jsi18n_url = reverse('admin:jsi18n')
    jquery_ui = static('treebeard/jquery-ui-1.8.5.custom.min.js')

    # Jquery UI is needed to call disableSelection() on drag and drop so
    # text selections arent marked while dragging a table row
    # http://www.lokkju.com/blog/archives/143
    TEMPLATE = (
        '<script type="text/javascript" src="{}"></script>'
        '<script type="text/javascript" src="{}"></script>'
        '<script>'
        '(function($){{jQuery = $.noConflict(true);}})(django.jQuery);'
        '</script>'
        '<script type="text/javascript" src="{}"></script>')
    return format_html(
        TEMPLATE, jsi18n_url, mark_safe(js_file), mark_safe(jquery_ui))


admin_tree.treebeard_js = treebeard_js
