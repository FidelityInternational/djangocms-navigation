from django.template import Template
from django.test import RequestFactory, TestCase

from cms.test_utils.testcases import CMSTestCase
from cms.test_utils.util.mock import AttributeObject
from menus.menu_pool import menu_pool

from djangocms_versioning.constants import (
    ARCHIVED,
    DRAFT,
    PUBLISHED,
    UNPUBLISHED,
)

from djangocms_navigation.cms_menus import CMSMenu
from djangocms_navigation.test_utils import factories

from .utils import disable_versioning_for_navigation


class CMSMenuTestCase(TestCase):
    def setUp(self):
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
            attr={"link_target": child1.link_target, "soft_root": False},
        )
        self.assertNavigationNodeEqual(
            nodes[3],
            title=grandchild.title,
            url=grandchild.content.get_absolute_url(),
            id=grandchild.id,
            parent_id=child1.id,
            attr={"link_target": grandchild.link_target, "soft_root": False},
        )
        self.assertNavigationNodeEqual(
            nodes[4],
            title=child2.title,
            url=child2.content.get_absolute_url(),
            id=child2.id,
            parent_id=menu_contents[1].menu.root_id,
            attr={"link_target": child2.link_target, "soft_root": False},
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
            attr={"link_target": child1.link_target, "soft_root": False},
        )
        self.assertNavigationNodeEqual(
            nodes[3],
            title=grandchild.title,
            url=grandchild.content.get_absolute_url(),
            id=grandchild.id,
            parent_id=child1.id,
            attr={"link_target": grandchild.link_target, "soft_root": False},
        )
        self.assertNavigationNodeEqual(
            nodes[4],
            title=child2.title,
            url=child2.content.get_absolute_url(),
            id=child2.id,
            parent_id=menu_versions[1].content.menu.root_id,
            attr={"link_target": child2.link_target, "soft_root": False},
        )

    def get_nodes_with_soft_root_for_versioning_enabled(self):
        """
        Check getnodes with a soft root node
        """
        menu_versions = factories.MenuVersionFactory.create_batch(2, state=PUBLISHED)
        child1 = factories.ChildMenuItemFactory(parent=menu_versions[0].content.root)
        child2 = factories.ChildMenuItemFactory(parent=menu_versions[1].content.root)
        grandchild = factories.ChildMenuItemFactory(parent=child1, soft_root=True)

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
            attr={"link_target": child1.link_target, "soft_root": False},
        )
        self.assertNavigationNodeEqual(
            nodes[3],
            title=grandchild.title,
            url=grandchild.content.get_absolute_url(),
            id=grandchild.id,
            parent_id=child1.id,
            attr={"link_target": grandchild.link_target, "soft_root": True},
        )
        self.assertNavigationNodeEqual(
            nodes[4],
            title=child2.title,
            url=child2.content.get_absolute_url(),
            id=child2.id,
            parent_id=menu_versions[1].content.menu.root_id,
            attr={"link_target": child2.link_target, "soft_root": False},
        )

    def test_get_roots_with_draft_mode_not_active(self):
        """This test to check versioning would group all the versions
        of menu content and return latest of all distinct menu content
        when renderer draft_mode_active is false
        """
        menucontent_1_v1 = factories.MenuVersionFactory(state=ARCHIVED)
        factories.MenuVersionFactory(
            content__menu=menucontent_1_v1.content.menu, state=DRAFT
        )
        menucontent_2_v1 = factories.MenuVersionFactory(state=PUBLISHED)
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
        menucontent_1_v1 = factories.MenuVersionFactory(state=ARCHIVED)
        menucontent_1_v2 = factories.MenuVersionFactory(
            content__menu=menucontent_1_v1.content.menu, state=DRAFT
        )
        menucontent_2_v1 = factories.MenuVersionFactory(state=PUBLISHED)
        factories.MenuVersionFactory(state=UNPUBLISHED)

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
        menucontent_1 = factories.MenuContentFactory()
        menucontent_2 = factories.MenuContentFactory()
        menucontent_3 = factories.MenuContentFactory()
        child1 = factories.ChildMenuItemFactory(parent=menucontent_1.root)
        factories.ChildMenuItemFactory(parent=menucontent_2.root)
        factories.ChildMenuItemFactory(parent=child1)

        roots = self.menu.get_roots(self.request)
        self.assertEqual(roots.count(), 3)
        self.assertListEqual(
            list(roots), [menucontent_1.root, menucontent_2.root, menucontent_3.root]
        )


class SoftrootTests(CMSTestCase):
    """
       Tree in fixture :
               root
                   aaa
                       aaa1
                           ccc
                               ddd
                       aaa2
                   bbb
       In the fixture, all pages are "in_navigation", "published" and
       NOT-"soft_root".
       What is a soft root?
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
       """
    def setUp(self):
        self.language = 'en'
        self.client.force_login(self.get_superuser())

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
            self.assertTreeQuality(n1.children, n2.children, 'level', 'title')

    def test_menu_without_softroots(self):
        """
        Tree in fixture :
               root
                   aaa
                       aaa1
                           ccc
                               ddd
                       aaa2
                   bbb
        tag: show_menu 0 100 0 100
        expected result 1:
               0:root
                  1:aaa
                     2:aaa1
                        3:ccc
                           4:ddd
                     5:aaa2
                  6:bbb
        """
        root_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="root",
            menu_title="root",
            page_title="root",
            version__state=PUBLISHED,
        )
        aaa_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="aaa",
            menu_title="aaa",
            page_title="aaa",
            version__state=PUBLISHED
        )
        ddd_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="ddd",
            menu_title="ddd",
            page_title="ddd",
            version__state=PUBLISHED
        )
        aaa1_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="aaa1",
            menu_title="aaa1",
            page_title="aaa1",
            version__state=PUBLISHED
        )
        aaa2_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="aaa2",
            menu_title="aaa2",
            page_title="aaa2",
            version__state=PUBLISHED
        )
        bbb_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="bbb",
            menu_title="bbb",
            page_title="bbb",
            version__state=PUBLISHED
        )
        ccc_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="ccc",
            menu_title="ccc",
            page_title="ccc",
            version__state=PUBLISHED
        )
        menu_content = factories.MenuContentWithVersionFactory(version__state=PUBLISHED)
        root = factories.ChildMenuItemFactory(parent=menu_content.root, content=root_pagecontent.page)
        aaa = factories.ChildMenuItemFactory(parent=root, content=aaa_pagecontent.page)
        aaa1 = factories.ChildMenuItemFactory(parent=aaa, content=aaa1_pagecontent.page)
        ccc = factories.ChildMenuItemFactory(parent=aaa1, content=ccc_pagecontent.page)
        ddd = factories.ChildMenuItemFactory(parent=ccc, content=ddd_pagecontent.page)
        aaa2 = factories.ChildMenuItemFactory(parent=aaa, content=aaa2_pagecontent.page)
        bbb = factories.ChildMenuItemFactory(parent=root, content=bbb_pagecontent.page)

        page = aaa_pagecontent.page
        context = self.get_context(page.get_absolute_url(), page=page)
        tpl = Template("{% load menu_tags %}{% show_menu 0 100 100 100 %}")
        tpl.render(context)
        hard_root = context['children']

        mock_tree = [
            AttributeObject(title=root.title, level=0, children=[
                AttributeObject(title=aaa.title, level=1, children=[
                    AttributeObject(title=aaa1.title, level=2, children=[
                        AttributeObject(title=ccc.title, level=3, children=[
                            AttributeObject(title=ddd.title, level=4, children=[])
                        ])
                    ]),
                    AttributeObject(title=aaa2.title, level=2, children=[])
                ]),
                AttributeObject(title=bbb.title, level=1, children=[])
            ])
        ]

        self.assertTreeQuality(hard_root, mock_tree, 'level', 'title')

    def test_menu_with_softroot_page_rendering(self):
        """
        Tree in fixture :
               root
                   aaa (soft_root)
                       aaa1
                           ccc
                               ddd
                       aaa2
                   bbb
        tag: show_menu 0 100 100 100
        expected result 1:
                     1:aaa1
                        2:ccc
                           3:ddd
                     3:aaa2
        """
        root_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="root",
            menu_title="root",
            page_title="root",
            version__state=PUBLISHED,
        )
        aaa_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="aaa",
            menu_title="aaa",
            page_title="aaa",
            version__state=PUBLISHED
        )
        ddd_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="ddd",
            menu_title="ddd",
            page_title="ddd",
            version__state=PUBLISHED
        )
        aaa1_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="aaa1",
            menu_title="aaa1",
            page_title="aaa1",
            version__state=PUBLISHED
        )
        aaa2_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="aaa2",
            menu_title="aaa2",
            page_title="aaa2",
            version__state=PUBLISHED
        )
        bbb_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="bbb",
            menu_title="bbb",
            page_title="bbb",
            version__state=PUBLISHED
        )
        ccc_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="ccc",
            menu_title="ccc",
            page_title="ccc",
            version__state=PUBLISHED
        )
        menu_content_ver = factories.MenuContentWithVersionFactory(version__state=PUBLISHED)
        root = factories.ChildMenuItemFactory(parent=menu_content_ver.root, content=root_pagecontent.page)
        aaa = factories.ChildMenuItemFactory(parent=root, soft_root=True, content=aaa_pagecontent.page)
        aaa1 = factories.ChildMenuItemFactory(parent=aaa, content=aaa1_pagecontent.page)
        ccc = factories.ChildMenuItemFactory(parent=aaa1, content=ccc_pagecontent.page)
        ddd = factories.ChildMenuItemFactory(parent=ccc, content=ddd_pagecontent.page)
        aaa2 = factories.ChildMenuItemFactory(parent=aaa, content=aaa2_pagecontent.page)
        factories.ChildMenuItemFactory(parent=root, content=bbb_pagecontent.page)

        page = aaa_pagecontent.page
        context = self.get_context(page.get_absolute_url(), page=page)
        tpl = Template("{% load menu_tags %}{% show_menu 0 100 100 100 %}")
        tpl.render(context)
        soft_root = context['children']

        mock_tree = [
            AttributeObject(title=aaa.title, level=0, children=[
                AttributeObject(title=aaa1.title, level=1, children=[
                    AttributeObject(title=ccc.title, level=2, children=[
                        AttributeObject(title=ddd.title, level=3, children=[])
                    ])
                ]),
                AttributeObject(title=aaa2.title, level=1, children=[]),
                ])
        ]

        self.assertTreeQuality(soft_root, mock_tree, 'level', 'title')

    def test_menu_with_softroot_rendering_nested_softroot_child(self):
        """
        Tree in fixture :
               root
                   aaa (soft_root)
                       aaa1
                           ccc
                               ddd
                       aaa2
                   bbb
        tag: show_menu 0 100 100 100
        expected result 1:
                    0:aaa
                     1:aaa1
                        2:ccc
                           3:ddd
                     3:aaa2
        """
        root_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="root",
            menu_title="root",
            page_title="root",
            version__state=PUBLISHED,
        )
        aaa_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="aaa",
            menu_title="aaa",
            page_title="aaa",
            version__state=PUBLISHED
        )
        ddd_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="ddd",
            menu_title="ddd",
            page_title="ddd",
            version__state=PUBLISHED
        )
        aaa1_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="aaa1",
            menu_title="aaa1",
            page_title="aaa1",
            version__state=PUBLISHED
        )
        aaa2_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="aaa2",
            menu_title="aaa2",
            page_title="aaa2",
            version__state=PUBLISHED
        )
        bbb_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="bbb",
            menu_title="bbb",
            page_title="bbb",
            version__state=PUBLISHED
        )
        ccc_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="ccc",
            menu_title="ccc",
            page_title="ccc",
            version__state=PUBLISHED
        )
        menu_content_version = factories.MenuContentWithVersionFactory(version__state=PUBLISHED)
        root = factories.ChildMenuItemFactory(parent=menu_content_version.root, content=root_pagecontent.page)
        aaa = factories.ChildMenuItemFactory(parent=root, soft_root=True, content=aaa_pagecontent.page)
        aaa1 = factories.ChildMenuItemFactory(parent=aaa, content=aaa1_pagecontent.page)
        ccc = factories.ChildMenuItemFactory(parent=aaa1, soft_root=True, content=ccc_pagecontent.page)
        ddd = factories.ChildMenuItemFactory(parent=ccc, content=ddd_pagecontent.page)
        factories.ChildMenuItemFactory(parent=aaa, content=aaa2_pagecontent.page)
        factories.ChildMenuItemFactory(parent=root, content=bbb_pagecontent.page)

        page = ddd_pagecontent.page
        context = self.get_context(page.get_absolute_url(), page=page)
        tpl = Template("{% load menu_tags %}{% show_menu 0 100 100 100 %}")
        tpl.render(context)

        soft_root = context['children']

        mock_tree = [
            AttributeObject(title=ccc.title, level=0, children=[
                AttributeObject(title=ddd.title, level=1, children=[])
            ])
        ]

        self.assertTreeQuality(soft_root, mock_tree, 'title', 'level')

    def test_basic_projects_softroot_rendering_nodes(self):
        """
        Given the tree:

        |- Home
        | |- Projects (SOFTROOT)
        | | |- django CMS
        | | |- django Shop
        | |- People

        Expected menu when on "Projects" (0 100 100 100):

        |- Projects (SOFTROOT)
        | |- django CMS
        | |- django Shop
        """
        root_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="root",
            menu_title="root",
            page_title="root",
            version__state=PUBLISHED,
        )
        projects_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="projects",
            menu_title="projects",
            page_title="projects",
            version__state=PUBLISHED
        )
        djangocms_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="djangocms",
            menu_title="djangocms",
            page_title="djangocms",
            version__state=PUBLISHED
        )
        djangoshop_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="djangoshop",
            menu_title="djangoshop",
            page_title="djangoshop",
            version__state=PUBLISHED
        )
        people_pagecontent = factories.PageContentWithVersionFactory(
            language=self.language,
            version__created_by=self.get_superuser(),
            title="people",
            menu_title="people",
            page_title="people",
            version__state=PUBLISHED
        )
        menu_version = factories.MenuContentWithVersionFactory(version__state=PUBLISHED)
        root = factories.ChildMenuItemFactory(parent=menu_version.root, content=root_pagecontent.page)
        projects = factories.ChildMenuItemFactory(parent=root, soft_root=True, content=projects_pagecontent.page)
        djangocms = factories.ChildMenuItemFactory(parent=projects, content=djangocms_pagecontent.page)
        djangoshop = factories.ChildMenuItemFactory(parent=projects, content=djangoshop_pagecontent.page)
        factories.ChildMenuItemFactory(parent=root, content=people_pagecontent.page)
        # On Projects

        page = projects_pagecontent.page
        context = self.get_context(page.get_absolute_url(), page=page)
        tpl = Template("{% load menu_tags %}{% show_menu 0 100 100 100 %}")
        tpl.render(context)

        nodes = context['children']
        # check everything

        self.assertEqual(len(nodes), 1)

        rootnode = nodes[0]

        self.assertEqual(rootnode.id, projects.id)

        self.assertEqual(len(rootnode.children), 2)

        cmsnode, shopnode = rootnode.children

        self.assertEqual(cmsnode.id, djangocms.id)

        self.assertEqual(shopnode.id, djangoshop.id)

        self.assertEqual(len(cmsnode.children), 0)

        self.assertEqual(len(shopnode.children), 0)
