from django.test import RequestFactory

from cms.test_utils.testcases import CMSTestCase

from djangocms_navigation.cms_menus import CMSMenu
from djangocms_navigation.test_utils import factories

from .utils import disable_versioning_for_navigation


class CMSMenuTestCase(CMSTestCase):
    def setUp(self):
        self.menu = CMSMenu(None)
        self.request = RequestFactory().get("/")
        self.user = self.get_superuser()
        self.client.force_login(self.user)

    def assertNavigationNodeEqual(self, node, **kwargs):
        """Helper method for asserting NavigationNode objects"""
        self.assertEqual(node.title, kwargs["title"])
        self.assertEqual(node.url, kwargs["url"])
        self.assertEqual(node.id, kwargs["id"])
        self.assertEqual(node.parent_id, kwargs["parent_id"])
        self.assertDictEqual(node.attr, kwargs["attr"])

    def test_get_nodes(self):
        menu_contents = factories.MenuContentFactory.create_batch(2)
        child1 = factories.ChildMenuItemFactory(parent=menu_contents[0].root)
        child2 = factories.ChildMenuItemFactory(parent=menu_contents[1].root)
        grandchild = factories.ChildMenuItemFactory(parent=child1)

        nodes = self.menu.get_nodes(self.request)

        self.assertEqual(len(nodes), 5)
        self.assertNavigationNodeEqual(
            nodes[0],
            title="",
            url="",
            id=menu_contents[0].menu.root_id,
            parent_id=None,
            attr={},
        )
        self.assertNavigationNodeEqual(
            nodes[1],
            title="",
            url="",
            id=menu_contents[1].menu.root_id,
            parent_id=None,
            attr={},
        )
        self.assertNavigationNodeEqual(
            nodes[2],
            title=child1.title,
            url=child1.content.get_absolute_url(),
            id=child1.id,
            parent_id=menu_contents[0].menu.root_id,
            attr={"link_target": child1.link_target},
        )
        self.assertNavigationNodeEqual(
            nodes[3],
            title=grandchild.title,
            url=grandchild.content.get_absolute_url(),
            id=grandchild.id,
            parent_id=child1.id,
            attr={"link_target": grandchild.link_target},
        )
        self.assertNavigationNodeEqual(
            nodes[4],
            title=child2.title,
            url=child2.content.get_absolute_url(),
            id=child2.id,
            parent_id=menu_contents[1].menu.root_id,
            attr={"link_target": child2.link_target},
        )

    def test_get_roots_with_multiple_menucontents(self):
        """test to check get_roots while creating two menu contents"""
        factories.MenuContentFactory()
        factories.MenuContentFactory()
        roots = self.menu.get_roots(self.request)
        self.assertEqual(roots.count(), 2)


class CMSMenuVersioningTestCase(CMSTestCase):
    def setUp(self):
        self.menu = CMSMenu(None)
        self.request = RequestFactory().get("/")
        self.user = self.get_superuser()

        # setting up menu content with versions
        menuitem_1 = factories.RootMenuItemFactory()
        menuitem_1_v1 = factories.MenuVersionFactory(content__root=menuitem_1)
        menuitem_1_v1.archive(self.user)
        menuitem_1_v1.copy(self.user)
        menuitem_2 = factories.RootMenuItemFactory()
        factories.MenuVersionFactory(content__root=menuitem_2)

    def test_get_roots_with_versioning_enabled(self):
        """This test to check versioning would group all the versions
        of menu content and return latest of all distinct menu content
        """
        roots = self.menu.get_roots(self.request)
        self.assertEqual(roots.count(), 2)

    @disable_versioning_for_navigation()
    def test_get_roots_with_versioning_disabled(self):
        """This test will check while versioning disabled it should check
        against all menu content created
        """
        roots = self.menu.get_roots(self.request)
        self.assertEqual(roots.count(), 3)
