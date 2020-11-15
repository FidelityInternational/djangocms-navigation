from django import template
from django.contrib.admin.templatetags.base import InclusionAdminNode
from django.contrib.admin.templatetags.admin_modify import submit_row

register = template.Library()


@register.tag(name='nav_submit_row')
def submit_row_tag(parser, token):
    return InclusionAdminNode(
        parser,
        token,
        func=submit_row,
        template_name='nav_delete_submit_line.html'
    )
