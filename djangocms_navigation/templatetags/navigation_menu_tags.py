# -*- coding: utf-8 -*-
from django import template

from cms.models import Page
from menus.menu_pool import menu_pool

from classytags.arguments import Argument
from classytags.core import Options
from classytags.helpers import InclusionTag

from djangocms_navigation.helpers import (
    get_navigation_node_for_content_object,
    get_root_node,
    get_site_menu_content
)
from djangocms_navigation.models import MenuContent, MenuItem

register = template.Library()


class NavigationShowBreadcrumb(InclusionTag):
    """
    Shows the breadcrumb from the node that has the same url as the current request

    - start level: after which level should the breadcrumb start? 0=home
    - template: template used to render the breadcrumb
    """
    name = 'navigation_breadcrumb'
    template = 'menu/dummy.html'

    options = Options(
        Argument('start_level', default=0, required=False),
        Argument('template', default='menu/breadcrumb.html', required=False),
        Argument('only_visible', default=True, required=False),
    )

    def get_context(self, context, start_level, template, only_visible):
        try:
            # If there's an exception (500), default context_processors may not be called.
            request = context['request']
        except KeyError:
            return {'template': 'cms/content.html'}
        if not (isinstance(start_level, int) or start_level.isdigit()):
            only_visible = template
            template = start_level
            start_level = 0
        try:
            only_visible = bool(int(only_visible))
        except ValueError:
            only_visible = bool(only_visible)
        ancestors = []

        menu_renderer = context.get('cms_menu_renderer')

        if not menu_renderer:
            menu_renderer = menu_pool.get_renderer(request)

        nodes = menu_renderer.get_nodes(breadcrumb=True)

        # Find home
        home = None
        for node in nodes:
            if node.content and isinstance(node.content, Page) and node.content.is_home:
                home = node
                break

        # Find selected
        selected = None
        selected = next((node for node in nodes if node.selected), None)
        if selected and selected != home:
            node = selected
            while node:
                # Added  to ancestors only if node content is mapped to page/url and visible
                if node.content and node.visible or not only_visible:
                    ancestors.append(node)
                node = node.parent
        if not ancestors or (ancestors and ancestors[-1] != home) and home:
            ancestors.append(home)
        ancestors.reverse()
        if len(ancestors) >= start_level:
            ancestors = ancestors[start_level:]
        else:
            ancestors = []
        context['ancestors'] = ancestors
        context['template'] = template
        return context


register.tag(NavigationShowBreadcrumb)


@register.simple_tag(takes_context=True)
def get_menu_node_for_page(context, page=None):
    request = context['request']
    page = page or request.current_page
    menu_content = get_site_menu_content(request, MenuContent)
    node = get_navigation_node_for_content_object(menu_content, page)
    if node:
        return node
    return None


@register.simple_tag(takes_context=True)
def get_root_node_for_page(context, page=None):
    request = context['request']
    page = page or request.current_page
    menu_content = get_site_menu_content(request, MenuContent)
    node = get_navigation_node_for_content_object(menu_content, page)
    if node:
        page_root_node = get_root_node(node, menu_content, MenuItem)
        return page_root_node
    return None
