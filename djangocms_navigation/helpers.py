from django.contrib.contenttypes.models import ContentType

from .models import MenuItem


def search_content_object_from_node_tree(menu_content, content_object):
    """
    Search for the content_object in menu_content node tree
    Input:  Menu content node tree , Content object to be searched
    Output: Node mapped to Content object if found in Node Tree else return False
    """

    content_object_content_type = ContentType.objects.get_for_model(content_object)
    root = MenuItem.get_root_nodes().filter(menucontent=menu_content).first()
    if root:
        child_nodes = root.get_descendants()
        search_node = child_nodes.filter(content_type=content_object_content_type, object_id=content_object.pk).first()
        if search_node:
            return search_node

    return False