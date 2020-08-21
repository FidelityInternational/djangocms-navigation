from django.db.models import Q

from cms.cms_menus import CMSMenu as OriginalCMSMenu
from cms.utils import get_current_site, get_language_from_request
from menus.base import Menu, Modifier, NavigationNode
from menus.menu_pool import menu_pool

from djangocms_versioning.constants import DRAFT, PUBLISHED

from .models import MenuContent, MenuItem
from .utils import get_versionable_for_content


class MenuItemNavigationNode(NavigationNode):

    def __init__(self, *args, **kwargs):
        self.content = kwargs.pop('content')
        super().__init__(*args, **kwargs)

    def is_selected(self, request):
        try:
            content = request.current_page
        except AttributeError:
            return False
        return content == self.content


class CMSMenu(Menu):
    menu_content_model = MenuContent
    menu_item_model = MenuItem

    def get_roots(self, request):
        language = get_language_from_request(request)
        queryset = self.menu_item_model.get_root_nodes().filter(
            menucontent__menu__site=get_current_site()
        )
        versionable = get_versionable_for_content(self.menu_content_model)
        if versionable:
            inner_filter = {
                "versions__state__in": [PUBLISHED],
                "language": language,
            }
            if self.renderer.draft_mode_active:
                inner_filter["versions__state__in"] += [DRAFT]
            menucontents = versionable.distinct_groupers(**inner_filter)
            queryset = queryset.filter(menucontent__in=menucontents)
        return queryset

    def get_menu_nodes(self, roots):
        root_paths = roots.values_list("path", flat=True)
        path_q = Q()
        for path in root_paths:
            path_q |= Q(path__startswith=path) & ~Q(path=path)
        return self.menu_item_model.get_tree().filter(path_q).order_by("path")

    def get_navigation_nodes(self, nodes, root_ids):
        for node in nodes:
            parent = node.get_parent()
            url = node.content.get_absolute_url() if node.content else ""
            if parent.id in root_ids:
                parent_id = root_ids[parent.id]
            else:
                parent_id = parent.id
            yield MenuItemNavigationNode(
                title=node.title,
                url=url,
                id=node.pk,
                parent_id=parent_id,
                content=node.content,
                visible=not node.hide_node,
                attr={
                    "link_target": node.link_target,
                    "soft_root": node.soft_root,
                    "is_home": node.is_home
                },
            )

    def get_nodes(self, request):
        navigations = self.get_roots(request)
        root_navigation_nodes = []
        root_ids = {}
        for navigation in navigations:
            identifier = navigation.menucontent.menu.root_id
            node = MenuItemNavigationNode(title="", url="", id=identifier, content=None)
            root_navigation_nodes.append(node)
            root_ids[navigation.pk] = identifier
        menu_nodes = self.get_menu_nodes(navigations)
        return root_navigation_nodes + list(
            self.get_navigation_nodes(menu_nodes, root_ids)
        )


class NavigationSelector(Modifier):
    """Select correct navigation tree.

    NavigationMenu has to return nodes from all relevant menus.
    This modifier restricts returned nodes to selected menu
    (via namespace parameter).
    """

    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        if post_cut or root_id or not nodes:
            return nodes
        if namespace:
            tree_id = namespace
        else:
            # defaulting to first subtree
            tree_id = nodes[0].id
        root = next(n for n in nodes if n.id == tree_id)
        if breadcrumb:
            home = next((node for node in nodes if node.attr.get('is_home')), None)
            if home and not home.visible:
                home.visible = True
            return nodes
        selected = None
        selected = next((node for node in nodes if node.selected), None)
        if selected:
            # find the nearest root page for selected node and make it visible in Navigation
            root = self.find_ancestors_root_for_node(selected, nodes)
            root.visible = True
        if root.attr.get("soft_root", False):
            return nodes
        return [self.make_roots(node, root) for node in root.children]

    def find_ancestors_root_for_node(self, node, nodes):
        """
        Check ancestors for root of selected node
        """
        if node.parent:
            if node.parent.attr.get("soft_root", False):
                return node.parent
            node = self.find_ancestors_root_for_node(node.parent, nodes)
        return node

    def make_roots(self, node, previous_root):
        """Detach level 1 nodes from parent, making them roots"""
        if node.parent == previous_root:
            node.parent = None
        return node


menu_pool.menus.pop(OriginalCMSMenu.__name__)
menu_pool.register_menu(CMSMenu)
menu_pool.register_modifier(NavigationSelector)
