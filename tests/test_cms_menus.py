from django.test import RequestFactory, TestCase

from djangocms_navigation.cms_menus import CMSMenu, NavigationSelector
from djangocms_navigation.test_utils import factories


class CMSMenuTestCase(TestCase):
    def setUp(self):
        self.menu = CMSMenu(None)
        self.request = RequestFactory().get('/')

    def assertNavigationNodeEqual(self, node, **kwargs):
        """Helper method for asserting NavigationNode objects"""
        self.assertEqual(node.title, kwargs['title'])
        self.assertEqual(node.url, kwargs['url'])
        self.assertEqual(node.id, kwargs['id'])
        self.assertEqual(node.parent_id, kwargs['parent_id'])
        self.assertDictEqual(node.attr, kwargs['attr'])

    def test_get_nodes(self):
        menu_contents = factories.MenuContentFactory.create_batch(2)
        child1 = factories.ChildMenuItemFactory(parent=menu_contents[0].root)
        child2 = factories.ChildMenuItemFactory(parent=menu_contents[1].root)
        grandchild = factories.ChildMenuItemFactory(parent=child1)

        nodes = self.menu.get_nodes(self.request)

        self.assertEqual(len(nodes), 5)
        self.assertNavigationNodeEqual(
            nodes[0], title='', url='', id=menu_contents[0].menu.root_id,
            parent_id=None, attr={}
        )
        self.assertNavigationNodeEqual(
            nodes[1], title='', url='', id=menu_contents[1].menu.root_id,
            parent_id=None, attr={}
        )
        self.assertNavigationNodeEqual(
            nodes[2], title=child1.title, url=child1.content.get_absolute_url(),
            id=child1.id, parent_id=menu_contents[0].menu.root_id,
            attr={'link_target': child1.link_target}
        )
        self.assertNavigationNodeEqual(
            nodes[3], title=grandchild.title, url=grandchild.content.get_absolute_url(),
            id=grandchild.id, parent_id=child1.id,
            attr={'link_target': grandchild.link_target}
        )
        self.assertNavigationNodeEqual(
            nodes[4], title=child2.title, url=child2.content.get_absolute_url(),
            id=child2.id, parent_id=menu_contents[1].menu.root_id,
            attr={'link_target': child2.link_target}
        )

