from cms.test_utils.testcases import CMSTestCase
from django.conf import settings

from djangocms_navigation.helpers import search_content_object_from_node_tree
from djangocms_navigation.test_utils import factories
from djangocms_navigation.test_utils.polls.models import Poll, PollContent


class NodeTreeSearchTestCase(CMSTestCase):

    def setUp(self):
        self.language = settings.LANGUAGES[0][0]

    def test_page_content_type_in_node_tree(self):
        """
        Test to ensure correct node mapped to page content object is returned from node tree search
        """
        menu_contents = factories.MenuContentFactory()
        child1 = factories.ChildMenuItemFactory(parent=menu_contents.root)
        page_content = factories.PageContentWithVersionFactory(
            language=self.language, version__created_by=self.get_superuser()
        )
        child2 = factories.ChildMenuItemFactory(parent=menu_contents.root, content=page_content)

        result = search_content_object_from_node_tree(menu_contents, page_content)

        self.assertEqual(result, child2)

    def test_to_search_content_object_in_nested_node_tree_search(self):
        """
        Test to ensure first node is returned  if more than one node is mapped to content object from node tree search
        """
        menu_contents = factories.MenuContentFactory()
        child1 = factories.ChildMenuItemFactory(parent=menu_contents.root)
        page_content = factories.PageContentWithVersionFactory(
            language=self.language, version__created_by=self.get_superuser()
        )
        child2 = factories.ChildMenuItemFactory(parent=menu_contents.root)
        grandchild = factories.ChildMenuItemFactory(parent=child1)
        grandchild1 = factories.ChildMenuItemFactory(parent=grandchild)
        grandchild2 = factories.ChildMenuItemFactory(parent=grandchild1, content=page_content)

        result = search_content_object_from_node_tree(menu_contents, page_content)

        self.assertEqual(result, grandchild2)

    def test_content_object_not_found_in_node_tree(self):
        """
        Test to ensure False if returned  when no node is mapped to content object from node tree search
        """
        menu_contents = factories.MenuContentFactory()
        child1 = factories.ChildMenuItemFactory(parent=menu_contents.root)
        page_content = factories.PageContentWithVersionFactory(
            language=self.language, version__created_by=self.get_superuser()
        )
        child2 = factories.ChildMenuItemFactory(parent=menu_contents.root)

        result = search_content_object_from_node_tree(menu_contents, page_content)

        self.assertFalse(result)

        grandchild = factories.ChildMenuItemFactory(parent=child1)
        grandchild1 = factories.ChildMenuItemFactory(parent=grandchild)
        grandchild2 = factories.ChildMenuItemFactory(parent=grandchild1)

        result = search_content_object_from_node_tree(menu_contents, page_content)

        self.assertFalse(result)

    def test_content_object_mapped_to_more_than_node(self):
        """
        Test to ensure first node found returned when more than one node is mapped to content object from node tree search
        """
        menu_contents = factories.MenuContentFactory()
        child1 = factories.ChildMenuItemFactory(parent=menu_contents.root)
        page_content = factories.PageContentWithVersionFactory(
            language=self.language, version__created_by=self.get_superuser()
        )
        child2 = factories.ChildMenuItemFactory(parent=menu_contents.root)

        grandchild = factories.ChildMenuItemFactory(parent=child1, content=page_content)
        grandchild1 = factories.ChildMenuItemFactory(parent=grandchild)
        grandchild2 = factories.ChildMenuItemFactory(parent=grandchild1, content=page_content)

        result = search_content_object_from_node_tree(menu_contents, page_content)

        self.assertEqual(result, grandchild)

    def test_to_search_pollcontent_in_node_tree(self):
        """
        Test to ensure correct node mapped to poll content is returned from node tree search
        """
        poll = Poll.objects.create(name="Test poll")

        poll_content = PollContent.objects.create(
            poll=poll, language="en", text="example"
        )
        menu_contents = factories.MenuContentFactory()
        child1 = factories.ChildMenuItemFactory(parent=menu_contents.root)
        child2 = factories.ChildMenuItemFactory(parent=menu_contents.root, content=poll_content)

        result = search_content_object_from_node_tree(menu_contents, poll_content)

        self.assertEqual(result, child2)

    def test_to_search_content_object_with_nodes_mapped_to_diff_content_objects_in_node_tree(self):
        """
        Test to ensure correct node mapped content object is returned with different nodes mapp[efrom node tree search
        """

        poll = Poll.objects.create(name="Test poll")

        poll_content = PollContent.objects.create(
            poll=poll, language="en", text="example"
        )
        page_content = factories.PageContentWithVersionFactory(
            language=self.language, version__created_by=self.get_superuser()
        )
        menu_contents = factories.MenuContentFactory()
        child1 = factories.ChildMenuItemFactory(parent=menu_contents.root)
        child2 = factories.ChildMenuItemFactory(parent=menu_contents.root)

        grandchild = factories.ChildMenuItemFactory(parent=child1, content=page_content)
        grandchild1 = factories.ChildMenuItemFactory(parent=grandchild)
        grandchild2 = factories.ChildMenuItemFactory(parent=grandchild1, content=poll_content)

        result = search_content_object_from_node_tree(menu_contents, page_content)

        self.assertEqual(result, grandchild)

        result = search_content_object_from_node_tree(menu_contents, poll_content)

        self.assertEqual(result, grandchild2)
