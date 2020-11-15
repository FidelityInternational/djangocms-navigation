import django
from django import template


if django.VERSION >= (2, 1):
    from django.contrib.admin.templatetags.admin_modify import submit_row
    from django.contrib.admin.templatetags.base import InclusionAdminNode
else:
    from django.template.context import Context


register = template.Library()


if django.VERSION >= (2, 1):
    @register.tag(name='nav_submit_row')
    def submit_row_tag(parser, token):
        return InclusionAdminNode(
            parser,
            token,
            func=submit_row,
            template_name='nav_delete_submit_line.html'
        )
else:
    @register.inclusion_tag('admin/djangocms_navigation/menuitem/nav_delete_submit_line_dj20.html', takes_context=True)
    def nav_submit_row(context):
        """
        Displays the row of buttons for delete and save.
        """
        change = context['change']
        is_popup = context['is_popup']
        save_as = context['save_as']
        show_save = context.get('show_save', True)
        show_save_and_continue = context.get('show_save_and_continue', True)
        ctx = Context(context)
        ctx.update({
            'show_delete_link': (
                    not is_popup and context['has_delete_permission'] and
                    change and context.get('show_delete', True)
            ),
            'show_save_as_new': not is_popup and change and save_as,
            'show_save_and_add_another': (
                    context['has_add_permission'] and not is_popup and
                    (not save_as or context['add'])
            ),
            'show_save_and_continue': not is_popup and context['has_change_permission'] and show_save_and_continue,
            'show_save': show_save,
        })
        return ctx
