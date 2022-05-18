from django.template.response import TemplateResponse


def render_navigation_content(request, navigation_menu_content):
    template = 'djangocms_navigation/navigation_content_preview.html'
    context = {'navigation_menu_content': navigation_menu_content}
    return TemplateResponse(request, template, context)