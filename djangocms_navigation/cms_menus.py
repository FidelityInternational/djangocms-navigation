from django.db.models import Q

from cms.cms_menus import CMSMenu as OriginalCMSMenu
from cms.utils import get_current_site
from menus.base import Menu, Modifier, NavigationNode
from menus.menu_pool import menu_pool

from djangocms_versioning.constants import DRAFT, PUBLISHED

from .models import MenuContent, MenuItem
from .utils import get_versionable_for_content


class MenuItemNavigationNode(NavigationNode):

    def is_selected(self, request):
        try:
            content = request.current_page
        except AttributeError:
            return False
        #return page_id == self.id
        return self.attr.get("content") == content


class CMSMenu(Menu):
    menu_content_model = MenuContent
    menu_item_model = MenuItem

    def get_roots(self, request):
        queryset = self.menu_item_model.get_root_nodes().filter(
            menucontent__menu__site=get_current_site()
        )
        versionable = get_versionable_for_content(self.menu_content_model)
        if versionable:
            inner_filter = {"versions__state__in": [PUBLISHED]}
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
                attr={"link_target": node.link_target},
            )

    def get_nodes(self, request):
        navigations = self.get_roots(request)
        root_navigation_nodes = []
        root_ids = {}
        for navigation in navigations:
            identifier = navigation.menucontent.menu.root_id
            node = MenuItemNavigationNode(title="", url="", id=identifier)
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
        return [self.make_roots(node, root) for node in root.children]

    def make_roots(self, node, previous_root):
        """Detach level 1 nodes from parent, making them roots"""
        if node.parent == previous_root:
            node.parent = None
        return node


class NavigationSoftRootCutter(Modifier):
    """
    Ask evildmp/superdmp if you don't understand softroots!
    Softroot description from the docs:
        A soft root is a page that acts as the root for a menu navigation tree.
        Typically, this will be a page that is the root of a significant new
        section on your site.
        When the soft root feature is enabled, the navigation menu for any page
        will start at the nearest soft root, rather than at the real root of
        the site’s page hierarchy.
        This feature is useful when your site has deep page hierarchies (and
        therefore multiple levels in its navigation trees). In such a case, you
        usually don’t want to present site visitors with deep menus of nested
        items.
        For example, you’re on the page -Introduction to Bleeding-?, so the menu
        might look like this:
            School of Medicine
                Medical Education
                Departments
                    Department of Lorem Ipsum
                    Department of Donec Imperdiet
                    Department of Cras Eros
                    Department of Mediaeval Surgery
                        Theory
                        Cures
                        Bleeding
                            Introduction to Bleeding <this is the current page>
                            Bleeding - the scientific evidence
                            Cleaning up the mess
                            Cupping
                            Leaches
                            Maggots
                        Techniques
                        Instruments
                    Department of Curabitur a Purus
                    Department of Sed Accumsan
                    Department of Etiam
                Research
                Administration
                Contact us
                Impressum
        which is frankly overwhelming.
        By making -Department of Mediaeval Surgery-? a soft root, the menu
        becomes much more manageable:
            Department of Mediaeval Surgery
                Theory
                Cures
                    Bleeding
                        Introduction to Bleeding <current page>
                        Bleeding - the scientific evidence
                        Cleaning up the mess
                    Cupping
                    Leaches
                    Maggots
                Techniques
                Instruments
    """

    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        # only apply this modifier if we're pre-cut (since what we do is cut)
        # or if no id argument is provided, indicating {% show_menu_below_id %}
        if post_cut or root_id:
            return nodes
        selected = None
        root_nodes = []
        # find the selected node as well as all the root nodes
        for node in nodes:
            if node.selected:
                selected = node
            if not node.parent:
                root_nodes.append(node)

        # if we found a selected ...
        if selected:
            # and the selected is a softroot
            if selected.attr.get("soft_root", False):
                # get it's descendants
                nodes = selected.get_descendants()
                # remove the link to parent
                selected.parent = None
                # make the selected page the root in the menu
                nodes = [selected] + nodes
            else:
                # if it's not a soft root, walk ancestors (upwards!)
                nodes = self.find_ancestors_and_remove_children(selected, nodes)
        return nodes

    def find_and_remove_children(self, node, nodes):
        for child in node.children:
            if child.attr.get("soft_root", False):
                self.remove_children(child, nodes)
        return nodes

    def remove_children(self, node, nodes):
        for child in node.children:
            nodes.remove(child)
            self.remove_children(child, nodes)
        node.children = []

    def find_ancestors_and_remove_children(self, node, nodes):
        """
        Check ancestors of node for soft roots
        """
        if node.parent:
            if node.parent.attr.get("soft_root", False):
                nodes = node.parent.get_descendants()
                node.parent.parent = None
                nodes = [node.parent] + nodes
            else:
                nodes = self.find_ancestors_and_remove_children(
                    node.parent, nodes)
        else:
            for newnode in nodes:
                if newnode != node and not newnode.parent:
                    self.find_and_remove_children(newnode, nodes)
        for child in node.children:
            if child != node:
                self.find_and_remove_children(child, nodes)
        return nodes


menu_pool.menus.pop(OriginalCMSMenu.__name__)
menu_pool.register_menu(CMSMenu)
menu_pool.register_modifier(NavigationSelector)
menu_pool.register_modifier(NavigationSoftRootCutter)
