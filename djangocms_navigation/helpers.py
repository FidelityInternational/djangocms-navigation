from copy import deepcopy

from django.contrib.contenttypes.models import ContentType

from cms.utils import get_current_site, get_language_from_request

from djangocms_versioning import versionables
from djangocms_versioning.constants import DRAFT, PUBLISHED

from .models import MenuContent, MenuItem
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
