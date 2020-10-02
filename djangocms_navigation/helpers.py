from copy import deepcopy

from django.contrib.contenttypes.models import ContentType

from cms.utils import get_current_site, get_language_from_request

from djangocms_versioning import versionables
from djangocms_versioning.constants import DRAFT, PUBLISHED

from .models import MenuItem, MenuContent
from .utils import get_versionable_for_content


def get_navigation_node_for_content_object(menu_content, content_object, node_model=MenuItem):
    """
    Find a navigation node that contains a content_object in a Navigation menu

    :param menu_content: A MenuContent instance
    :param content_object: A content object registered in the cms_config
    :param node_model: A model used for a navigation item
    :return: A navigation node or False
    """

    root = node_model.get_root_nodes().filter(menucontent=menu_content).first()
    if root:
        content_object_content_type = ContentType.objects.get_for_model(content_object)
        child_nodes = root.get_descendants()
        search_node = child_nodes.filter(content_type=content_object_content_type, object_id=content_object.pk).first()
        if search_node:
            return search_node

    return False


def get_site_menu_content(request, content_model=MenuContent):
    """
    Find the menu Content grouper for the current site
    """
    current_lang = get_language_from_request(request)
    versionable = get_versionable_for_content(content_model)
    if versionable:
        inner_filter = {
            "versions__state__in": [PUBLISHED],
            "language": current_lang,
            "menu__site": get_current_site(),
        }
        if hasattr(request, "toolbar") and request.toolbar.edit_mode_active:
            inner_filter["versions__state__in"] = [DRAFT]
        menucontent = versionable.distinct_groupers(**inner_filter).first()
        return menucontent
    return None


def get_root_node(node, menu_content, node_model=MenuItem):
    """
    Find the nearest root for the node in menu.
    """
    root = node_model.get_root_nodes().filter(menucontent=menu_content).first()
    while node.get_parent() and node.get_parent() != root:
        if node.soft_root:
            return node
        node = node.get_parent()
    return node


def proxy_model(obj, content_model):
    """
    Get the proxy model from a

    :param obj: A registered versionable object
    :param content_model: A registered content model
    """
    versionable = versionables.for_content(content_model)
    obj_ = deepcopy(obj)
    obj_.__class__ = versionable.version_model_proxy
    return obj_
