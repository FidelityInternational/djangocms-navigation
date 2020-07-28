from django.template import Template
from django.test import RequestFactory, TestCase
from django.template.context import Context

from cms.test_utils.testcases import CMSTestCase
from cms.test_utils.util.mock import AttributeObject

from menus.menu_pool import menu_pool

from djangocms_navigation.cms_menus import CMSMenu
from djangocms_navigation.test_utils import factories

from .utils import disable_versioning_for_navigation


try:
    from djangocms_versioning.constants import ARCHIVED, DRAFT, UNPUBLISHED, PUBLISHED
except ImportError:
    ARCHIVED, DRAFT, UNPUBLISHED, PUBLISHED = None


class CMSMenuTestCase(TestCase):
    def setUp(self):
        self.language = "en"
        self.request = RequestFactory().get("/")
        self.user = factories.UserFactory()
        self.request.user = self.user
        self.renderer = menu_pool.get_renderer(self.request)
        self.menu = CMSMenu(self.renderer)

    def assertNavigationNodeEqual(self, node, **kwargs):
        """Helper method for asserting NavigationNode objects"""
        self.assertEqual(node.title, kwargs["title"])
        self.assertEqual(node.url, kwargs["url"])
        self.assertEqual(node.id, kwargs["id"])
        self.assertEqual(node.parent_id, kwargs["parent_id"])
        self.assertDictEqual(node.attr, kwargs["attr"])

    @disable_versioning_for_navigation()
    def test_get_nodes(self):
        menu_contents = factories.MenuContentFactory.create_batch(2, language=self.language)
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

    def get_nodes_for_versioning_enabled(self):
        menu_versions = factories.MenuVersionFactory.create_batch(2, state=PUBLISHED)
        child1 = factories.ChildMenuItemFactory(parent=menu_versions[0].content.root)
        child2 = factories.ChildMenuItemFactory(parent=menu_versions[1].content.root)
        grandchild = factories.ChildMenuItemFactory(parent=child1)

        nodes = self.menu.get_nodes(self.request)

        self.assertEqual(len(nodes), 5)
        self.assertNavigationNodeEqual(
            nodes[0],
            title="",
            url="",
            id=menu_versions[0].content.menu.root_id,
            parent_id=None,
            attr={},
        )
        self.assertNavigationNodeEqual(
            nodes[1],
            title="",
            url="",
            id=menu_versions[1].content.menu.root_id,
            parent_id=None,
            attr={},
        )
        self.assertNavigationNodeEqual(
            nodes[2],
            title=child1.title,
            url=child1.content.get_absolute_url(),
            id=child1.id,
            parent_id=menu_versions[0].content.menu.root_id,
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
            parent_id=menu_versions[1].content.menu.root_id,
            attr={"link_target": child2.link_target},
        )

    def test_get_roots_with_draft_mode_not_active(self):
        """This test to check versioning would group all the versions
        of menu content and return latest of all distinct menu content
        when renderer draft_mode_active is false
        """
        menucontent_1_v1 = factories.MenuVersionFactory(content__language=self.language,state=ARCHIVED)
        factories.MenuVersionFactory(
            content__menu=menucontent_1_v1.content.menu, content__language=self.language, state=DRAFT
        )
        menucontent_2_v1 = factories.MenuVersionFactory(content__language=self.language, state=PUBLISHED)
        factories.MenuVersionFactory(state=UNPUBLISHED)
        # Assert to check draft_mode_active is false
        self.assertFalse(self.menu.renderer.draft_mode_active)
        roots = self.menu.get_roots(self.request)

        # Renderer should only render published menucontent
        self.assertEqual(roots.count(), 1)
        self.assertListEqual(list(roots), [menucontent_2_v1.content.root])

    def test_get_roots_with_draft_mode_active(self):
        """This test to check versioning would group all the versions
        of menu content and return latest of all distinct menu content
        when renderer draft_mode_active is True
        """
        menucontent_1_v1 = factories.MenuVersionFactory(content__language=self.language, state=ARCHIVED)
        menucontent_1_v2 = factories.MenuVersionFactory(
            content__menu=menucontent_1_v1.content.menu, content__language=self.language, state=DRAFT
        )
        menucontent_2_v1 = factories.MenuVersionFactory(content__language=self.language, state=PUBLISHED)
        factories.MenuVersionFactory(content__language=self.language, state=UNPUBLISHED)

        # Getting renderer to set draft_mode_active
        renderer = self.renderer
        renderer.draft_mode_active = True
        menu = CMSMenu(renderer)

        roots = menu.get_roots(self.request)
        self.assertEqual(roots.count(), 2)
        self.assertListEqual(
            list(roots), [menucontent_1_v2.content.root, menucontent_2_v1.content.root]
        )

    @disable_versioning_for_navigation()
    def test_get_roots_with_versioning_disabled(self):
        """This test will check while versioning disabled it should assert
        against all menu content created
        """
        menucontent_1 = factories.MenuContentFactory(language="en")
        menucontent_2 = factories.MenuContentFactory(language="en")
        menucontent_3 = factories.MenuContentFactory(language="en")
        child1 = factories.ChildMenuItemFactory(parent=menucontent_1.root)
        factories.ChildMenuItemFactory(parent=menucontent_2.root)
        factories.ChildMenuItemFactory(parent=child1)

        roots = self.menu.get_roots(self.request)
        self.assertEqual(roots.count(), 3)
        self.assertListEqual(
            list(roots), [menucontent_1.root, menucontent_2.root, menucontent_3.root]
        )


class MultisiteNavigationTests(CMSTestCase):

    def assertTreeQuality(self, a, b, *attrs):
        """
        Checks that the node-lists a and b are the same for attrs.
        This is recursive over the tree
        """
        msg = '%r != %r with %r, %r' % (len(a), len(b), a, b)
        self.assertEqual(len(a), len(b), msg)
        for n1, n2 in zip(a, b):
            for attr in attrs:
                a1 = getattr(n1, attr)
                a2 = getattr(n2, attr)
                msg = '%r != %r with %r, %r (%s)' % (a1, a2, n1, n2, attr)
                self.assertEqual(a1, a2, msg)
            self.assertTreeQuality(n1.children, n2.children)

    def test_menu_with_multiple_languages(self):
        """
        Tree in site 1 language 1 fixture :
               root-en
                   aaa
                       aaa1
        Tree in site 1 language 2 fixture :
               root-it
                   bbb
                       bbb1
        """
        template = Template("{% load menu_tags %}{% show_menu 0 100 100 100 %}")
        # Site page navigation menu
        navigation_menu = factories.MenuFactory()
        # English page navigation tree, same menu
        root_pagecontent_en = factories.PageContentWithVersionFactory(
            language="en",
            version__created_by=self.get_superuser(),
            title="root-en",
            menu_title="root-en",
            page_title="root-en",
            version__state=PUBLISHED,
        )
        menu_content_en = factories.MenuContentWithVersionFactory(
            menu=navigation_menu, language="en", version__state=PUBLISHED)
        root_en = factories.ChildMenuItemFactory(
            parent=menu_content_en.root, title="root_en", content=root_pagecontent_en.page)
        aaa = factories.ChildMenuItemFactory(parent=root_en, title="aaa")
        aaa1 = factories.ChildMenuItemFactory(parent=aaa, title="aaa1")
        # Italian Page navigation tree, same menu
        root_pagecontent_it = factories.PageContentWithVersionFactory(
            language="it",
            version__created_by=self.get_superuser(),
            title="root-it",
            menu_title="root-it",
            page_title="root-it",
            version__state=PUBLISHED,
        )
        menu_content_it = factories.MenuContentWithVersionFactory(
            menu=navigation_menu, language="it", version__state=PUBLISHED)
        root_it = factories.ChildMenuItemFactory(
            parent=menu_content_it.root, title="root_it", content=root_pagecontent_it.page)
        bbb = factories.ChildMenuItemFactory(parent=root_it, title="bbb")
        bbb1 = factories.ChildMenuItemFactory(parent=bbb, title="bbb1")

        context_en_raw = {
            'request': self.get_request(
                root_pagecontent_en.page.get_absolute_url(language="en"), language="en", page=root_pagecontent_en.page)
        }
        context_en = Context(context_en_raw)
        template.render(context_en)

        mock_en_tree = [
            AttributeObject(title=root_en.title, level=0, children=[
                AttributeObject(title=aaa.title, level=1, children=[
                    AttributeObject(title=aaa1.title, level=2, children=[])
                ])
            ])
        ]

        self.assertTreeQuality(context_en['children'], mock_en_tree, 'title')

        context_it_raw = {
            'request': self.get_request(
                root_pagecontent_it.page.get_absolute_url(language="it"), language="it", page=root_pagecontent_it.page)
        }
        context_it = Context(context_it_raw)
        template.render(context_it)

        mock_it_tree = [
            AttributeObject(title=root_it.title, level=0, children=[
                AttributeObject(title=bbb.title, level=1, children=[
                    AttributeObject(title=aaa1.title, level=2, children=[])
                ])
            ])
        ]

        self.assertTreeQuality(context_it['children'], mock_it_tree, 'title')
