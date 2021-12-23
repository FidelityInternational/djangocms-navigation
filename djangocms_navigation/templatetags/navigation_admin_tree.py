# -*- coding: utf-8 -*-
from django import template
from django.template.loader import get_template
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.templatetags.static import static

from treebeard.templatetags import admin_tree

register = template.Library()

'''
This module is simply for overwriting some of treebeard's admin_tree templatetag functions
with djangocms_navigation specific values.
'''


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


t = get_template('djangocms_navigation/admin/tree_change_list_results.html')
admin_tree.register.inclusion_tag(t, takes_context=True)(admin_tree.result_tree)


@admin_tree.register.simple_tag
def treebeard_js():

    # Overwriting treebeard_js tag to insert navigation specific js file:
    js_file = static('djangocms_navigation/js/navigation-tree-admin.js')

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
        TEMPLATE, "jsi18n", mark_safe(js_file), mark_safe(jquery_ui))


admin_tree.treebeard_js = treebeard_js
