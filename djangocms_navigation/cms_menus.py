from cms.cms_menus import CMSMenu as OriginalCMSMenu
from cms.utils import get_current_site
from menus.base import Menu, Modifier, NavigationNode
from menus.menu_pool import menu_pool

from .models import Menu as MenuModel, MenuItem


class CMSMenu(Menu):
    def get_roots(self, request):
        return MenuModel.objects.filter(site=get_current_site())

    def get_menu_nodes(self, roots):
        return (
            MenuItem.get_tree()
            .filter(menu_content__in=roots.values("menucontent"))
            .order_by("menu_content", "path")
        )

    def get_navigation_nodes(self, nodes, root_nodes):
        for node in nodes:
            parent = node.get_parent()
            if parent:
                parent_id = parent.id
            else:
                parent_id = root_nodes[node.menu_content_id].id
            yield NavigationNode(
                title=node.title,
                url=node.content.get_absolute_url(),
                id=node.pk,
                parent_id=parent_id,
                attr={"link_target": node.link_target},
            )

    def get_nodes(self, request):
        navigations = self.get_roots(request)
        root_nodes = {}
        root_navigation_nodes = []
        for navigation in navigations:
            node = NavigationNode(
                title="", url="", id="root-{}".format(navigation.identifier)
            )
            root_navigation_nodes.append(node)
            root_nodes[navigation.pk] = node
        menu_nodes = self.get_menu_nodes(navigations)
        return root_navigation_nodes + list(
            self.get_navigation_nodes(menu_nodes, root_nodes)
        )


class NavigationSelector(Modifier):
    """Select correct navigation tree.

    NavigationMenu has to return nodes from all relevant menus.
    This modifier restricts returned nodes to selected menu
    (via namespace parameter).
    """

    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        if post_cut or root_id:
            return nodes
        if namespace:
            tree_id = namespace
        else:
            # defaulting to first subtree
            tree_id = nodes[0].id
        root = next(n for n in nodes if n.id == tree_id)
        return [self.make_roots(node, root) for node in root.children]

    def make_roots(self, node, previous_root):
        """Detach level 1 nodes from parent, making them roots"""
        if node.parent == previous_root:
            node.parent = None
        return node


menu_pool.menus.pop(OriginalCMSMenu.__name__)
menu_pool.register_menu(CMSMenu)
menu_pool.register_modifier(NavigationSelector)
