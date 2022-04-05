# -*- coding: utf-8 -*-

import datetime

from django.contrib.admin.templatetags.admin_list import (
    result_headers,
    result_hidden_fields,
)
from django.contrib.admin.utils import (
    display_for_field,
    display_for_value,
    lookup_field,
)
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.template import Library
from django.templatetags.static import static
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from treebeard.templatetags import admin_tree, needs_checkboxes
from treebeard.templatetags.admin_tree import check_empty_dict, results


register = Library()

"""
This module is simply for overwriting some of treebeard's admin_tree templatetag functions
with djangocms_navigation specific values.

CAVEAT: Treebeard encapulates markup in some of it's template tags, so we are needing
to keep the same approach in order to overwrite markup, ie. with get_space and get_collapse below.

INFO: get_result_and_row_class is an almost exact copy, with the exception of a field_name
function to allow proper str representation for callables included as part of list_display
on changelist views.
"""


def get_field_name(field_name):
    if callable(field_name):
        return field_name.__name__
    return field_name


def get_result_and_row_class(cl, field_name, result):
    empty_value_display = cl.model_admin.get_empty_value_display()
    row_classes = ['field-%s' % get_field_name(field_name)]
    try:
        f, attr, value = lookup_field(field_name, result, cl.model_admin)
    except ObjectDoesNotExist:
        result_repr = empty_value_display
    else:
        empty_value_display = getattr(attr, 'empty_value_display', empty_value_display)
        if f is None:
            if field_name == 'action_checkbox':
                row_classes = ['action-checkbox']
            allow_tags = getattr(attr, 'allow_tags', False)
            boolean = getattr(attr, 'boolean', False)
            result_repr = display_for_value(value, empty_value_display, boolean)
            # Strip HTML tags in the resulting text, except if the
            # function has an "allow_tags" attribute set to True.
            # WARNING: this will be deprecated in Django 2.0
            if allow_tags:
                result_repr = mark_safe(result_repr)
            if isinstance(value, (datetime.date, datetime.time)):
                row_classes.append('nowrap')
        else:
            if isinstance(getattr(f, 'remote_field'), models.ManyToOneRel):
                field_val = getattr(result, f.name)
                if field_val is None:
                    result_repr = empty_value_display
                else:
                    result_repr = field_val
            else:
                result_repr = display_for_field(value, f, empty_value_display)
            if isinstance(f, (models.DateField, models.TimeField,
                              models.ForeignKey)):
                row_classes.append('nowrap')
        if force_str(result_repr) == '':
            result_repr = mark_safe('&nbsp;')
    row_class = mark_safe(' class="%s"' % ' '.join(row_classes))
    return result_repr, row_class


admin_tree.get_result_and_row_class = get_result_and_row_class


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
    return {
        'filtered': not check_empty_dict(request.GET),
        'result_hidden_fields': list(result_hidden_fields(cl)),
        'result_headers': headers,
        'results': list(results(cl)),
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
