from django.template.response import TemplateResponse


def render_navigation_content(request, navigation_content):
    template = 'djangocms_navigation/navigation_content_preview.html'
    context = {'navigation_content': navigation_content}
    return TemplateResponse(request, template, context)