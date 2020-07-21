from django.conf import settings
from django.test import RequestFactory, TestCase

from menus.menu_pool import menu_pool

from cms.test_utils.testcases import CMSTestCase

from djangocms_navigation.cms_menus import CMSMenu
from djangocms_navigation.helpers import get_navigation_node_for_content_object
from djangocms_navigation.test_utils import factories
from djangocms_navigation.test_utils.polls.models import Poll, PollContent
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

from cms.models import Page, User
from cms.test_utils.testcases import CMSTestCase
from cms.utils.urlutils import admin_reverse

from djangocms_navigation.constants import SELECT2_CONTENT_OBJECT_URL_NAME
from djangocms_navigation.models import MenuItem
class NavigationContentTypeSearchTestCase(CMSTestCase):

    def setUp(self):
        self.language = settings.LANGUAGES[0][0]

    def test_page_content_type_in_node_tree(self):
        """
        The correct node mapped to page content object is returned by the helper
        """
        menu_contents = factories.MenuContentFactory()
        factories.ChildMenuItemFactory(parent=menu_contents.root)
        page_content = factories.PageContentWithVersionFactory(
            language=self.language, version__created_by=self.get_superuser()
        )
        child2 = factories.ChildMenuItemFactory(parent=menu_contents.root, content=page_content)

        result = get_navigation_node_for_content_object(menu_contents, page_content)

        self.assertEqual(result, child2)

    def test_to_search_content_object_in_nested_node_tree_search(self):
        """
        Correct node mapped is returned by the helper in nested node tree
        """
        menu_contents = factories.MenuContentFactory()
        child1 = factories.ChildMenuItemFactory(parent=menu_contents.root)
        page_content = factories.PageContentWithVersionFactory(
            language=self.language, version__created_by=self.get_superuser()
        )
        factories.ChildMenuItemFactory(parent=menu_contents.root)
        grandchild = factories.ChildMenuItemFactory(parent=child1)
        grandchild1 = factories.ChildMenuItemFactory(parent=grandchild)
        grandchild2 = factories.ChildMenuItemFactory(parent=grandchild1, content=page_content)

        result = get_navigation_node_for_content_object(menu_contents, page_content)

        self.assertEqual(result, grandchild2)

    def test_content_object_not_found_in_node_tree(self):
        """
        False is returned  by the helper when no node is mapped to content in node tree
        """
        menu_contents = factories.MenuContentFactory()
        child1 = factories.ChildMenuItemFactory(parent=menu_contents.root)
        page_content = factories.PageContentWithVersionFactory(
            language=self.language, version__created_by=self.get_superuser()
        )
        factories.ChildMenuItemFactory(parent=menu_contents.root)

        result = get_navigation_node_for_content_object(menu_contents, page_content)

        self.assertFalse(result)

        grandchild = factories.ChildMenuItemFactory(parent=child1)
        grandchild1 = factories.ChildMenuItemFactory(parent=grandchild)
        factories.ChildMenuItemFactory(parent=grandchild1)

        result = get_navigation_node_for_content_object(menu_contents, page_content)

        self.assertFalse(result)

    def test_content_object_mapped_to_more_than_node(self):
        """
        The First node found is returned by helper when more than one node is mapped to content object
        in node tree
        """
        menu_contents = factories.MenuContentFactory()
        child1 = factories.ChildMenuItemFactory(parent=menu_contents.root)
        page_content = factories.PageContentWithVersionFactory(
            language=self.language, version__created_by=self.get_superuser()
        )
        factories.ChildMenuItemFactory(parent=menu_contents.root)
        grandchild = factories.ChildMenuItemFactory(parent=child1, content=page_content)
        grandchild1 = factories.ChildMenuItemFactory(parent=grandchild)
        factories.ChildMenuItemFactory(parent=grandchild1, content=page_content)

        result = get_navigation_node_for_content_object(menu_contents, page_content)

        self.assertEqual(result, grandchild)

    def test_to_search_pollcontent_in_node_tree(self):
        """
        The correct node mapped to poll content is returned from node tree search
        """
        poll = Poll.objects.create(name="Test poll")
        poll_content = PollContent.objects.create(
            poll=poll, language="en", text="example"
        )
        menu_contents = factories.MenuContentFactory()
        factories.ChildMenuItemFactory(parent=menu_contents.root)
        child2 = factories.ChildMenuItemFactory(parent=menu_contents.root, content=poll_content)

        result = get_navigation_node_for_content_object(menu_contents, poll_content)

        self.assertEqual(result, child2)

    def test_to_search_content_object_with_nodes_mapped_to_diff_content_objects_in_node_tree(self):
        """
        Multiple different content types mixed in a navigation tree can be found correctly by the helper.
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
        factories.ChildMenuItemFactory(parent=menu_contents.root)
        grandchild = factories.ChildMenuItemFactory(parent=child1, content=page_content)
        grandchild1 = factories.ChildMenuItemFactory(parent=grandchild)
        grandchild2 = factories.ChildMenuItemFactory(parent=grandchild1, content=poll_content)

        result = get_navigation_node_for_content_object(menu_contents, page_content)

        self.assertEqual(result, grandchild)

        result = get_navigation_node_for_content_object(menu_contents, poll_content)

        self.assertEqual(result, grandchild2)


class TestNavigationPerformance(CMSTestCase):

        def setUp(self):
            self.request = RequestFactory().get("/")
            self.user = factories.UserFactory()
            self.request.user = self.user
            self.renderer = menu_pool.get_renderer(self.request)
            self.menu = CMSMenu(self.renderer)


            def test_select_node_from_deeply_nested_nodes(self):
                menu_contents = factories.MenuContentFactory()

                factories.ChildMenuItemFactory.create_batch(1000, parent=menu_contents.root)
                import pdb; pdb.set_trace()
                nodes = self.menu.get_nodes(self.request)
                nodes[501].__setattr__("soft_root", True)

                page_content = factories.PageContentWithVersionFactory(
                    language=self.language,
                    version__created_by=self.get_superuser(),
                    title="test",
                    menu_title="test",
                    page_title="test",
                )

                page_contenttype_id = ContentType.objects.get_for_model(Page).id

                nodes[501].content = page_content
                with self.login_user_context(self.superuser):
                    with self.assertNumQueries(500):
                        response = self.client.get(
                            self.select2_endpoint,
                            data={"content_type_id": page_contenttype_id, "query": "test2"},
                        )

                self.assertEqual(len(response.json()["results"]), 1)