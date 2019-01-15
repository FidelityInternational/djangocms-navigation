from django.test import TestCase

from djangocms_navigation.models import MenuItem
from djangocms_navigation.test_utils import factories


class CopyFunctionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = factories.UserFactory()

    def test_menu_content_object_gets_duplicated_with_its_root_menuitem(self):
        """The implementation of versioning for MenuContent correctly
        copies the MenuContent object and the root MenuItem object
        """
        original_version = factories.MenuVersionFactory()

        new_version = original_version.copy(self.user)

        # Created a new content record
        self.assertNotEqual(original_version.content.pk, new_version.content.pk)
        # Is version of the same menu as the original version
        self.assertEqual(original_version.content.menu, new_version.content.menu)
        # The root MenuItem has been duplicated into a new MenuItem
        original_root = original_version.content.root
        new_root = new_version.content.root
        self.assertNotEqual(original_root.pk, new_root.pk)
        self.assertEqual(original_root.title, new_root.title)
        self.assertIsNone(new_root.content)
        # The root is indeed a root node
        self.assertTrue(new_root.is_root())

    def test_child_menu_items_are_copied(self):
        """The implementation of versioning for MenuContent correctly
        copies child MenuItem objects
        """
        original_root = factories.RootMenuItemFactory()
        original_version = factories.MenuVersionFactory(content__root=original_root)
        original_child = factories.ChildMenuItemFactory(parent=original_root)

        new_version = original_version.copy(self.user)

        new_root = new_version.content.root
        # If this throws DoesNotExist then the child clearly wasn't duplicated
        new_child = MenuItem.objects.exclude(
            pk__in=[original_root.pk, original_child.pk, new_root.pk]
        ).get()
        # The fields in the child have been copied over correctly
        self.assertEqual(new_child.title, original_child.title)
        self.assertEqual(new_child.content, original_child.content)
        self.assertEqual(new_child.link_target, original_child.link_target)
        # The new child is indeed a child node of the new root
        self.assertTrue(new_child.is_child_of(new_root))

    def test_sibling_menu_items_are_copied(self):
        """The implementation of versioning for MenuContent correctly
        copies sibling MenuItem objects
        """
        original_root = factories.RootMenuItemFactory()
        original_version = factories.MenuVersionFactory(content__root=original_root)
        original_child = factories.ChildMenuItemFactory(parent=original_root)
        original_sibling = factories.SiblingMenuItemFactory(sibling=original_child)

        new_version = original_version.copy(self.user)

        new_root = new_version.content.root
        # If this throws DoesNotExist then the sibling clearly wasn't duplicated
        new_sibling = MenuItem.objects.get(
            path=new_root.path + original_sibling.path[4:]
        )
        # The fields in the sibling have been copied over correctly
        self.assertEqual(new_sibling.title, original_sibling.title)
        self.assertEqual(new_sibling.content, original_sibling.content)
        self.assertEqual(new_sibling.link_target, original_sibling.link_target)
        # The new sibling is indeed a sibling node of the new child
        new_child = MenuItem.objects.get(path=new_root.path + original_child.path[4:])
        self.assertTrue(new_child.is_sibling_of(new_child))

    def test_very_nested_menu_items_are_copied(self):
        """The implementation of versioning for MenuContent correctly
        copies very nested MenuItem structures
        """
        original_version = factories.MenuVersionFactory()
        original_item1 = factories.ChildMenuItemFactory(
            parent=original_version.content.root
        )
        original_item2 = factories.SiblingMenuItemFactory(sibling=original_item1)
        original_item11 = factories.ChildMenuItemFactory(parent=original_item1)
        original_item111 = factories.ChildMenuItemFactory(parent=original_item11)
        original_item112 = factories.ChildMenuItemFactory(parent=original_item11)
        original_item1111 = factories.ChildMenuItemFactory(parent=original_item111)
        # TODO: This causes an inconsistent integrity error, it happens about
        # 50-70% of the time. I thought it was the factory, but using
        # the add_child method does the same
        original_item21 = original_item2.add_child(title="21")
        original_item22 = factories.SiblingMenuItemFactory(sibling=original_item21)

        new_version = original_version.copy(self.user)

        # TODO: Not a great way of testing this really
        root_path = new_version.content.root.path
        expected_paths = [
            root_path + item.path[4:]
            for item in MenuItem.get_tree(original_version.content.root)
        ]
        new_paths = [item.path for item in MenuItem.get_tree(new_version.content.root)]
        self.assertListEqual(new_paths, expected_paths)
