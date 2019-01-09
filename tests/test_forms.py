from cms.test_utils.testcases import CMSTestCase

from djangocms_navigation.forms import MenuItemForm
from djangocms_navigation.test_utils import factories


class MenuContentFormTestCase(CMSTestCase):
    # Todo: add more test while change object field to autocomplete

    def setUp(self):
        self.menu_root = factories.RootMenuItemFactory()

    def test_valid_if_adding_child_of_existing_root_node(self):
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": self.menu_root.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_valid_if_adding_child_of_existing_child_node(self):
        item = factories.ChildMenuItemFactory(parent=self.menu_root)
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": item.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_valid_if_adding_right_sibling_of_existing_child_node(self):
        item = factories.ChildMenuItemFactory(parent=self.menu_root)
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": item.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "right",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_valid_if_adding_left_sibling_of_existing_child_node(self):
        item = factories.ChildMenuItemFactory(parent=self.menu_root)
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": item.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "left",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_valid_if_changing_existing_root_node(self):
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": self.menu_root.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(
            menu_root=self.menu_root, data=data, instance=self.menu_root)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_valid_if_changing_existing_child_node(self):
        item = factories.ChildMenuItemFactory(parent=self.menu_root)
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": item.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(
            menu_root=self.menu_root, data=data, instance=item)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_invalid_if_no_relative_node_specified_and_child_position(self):
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": 0,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn('_ref_node_id', form.errors)
        self.assertListEqual(
            form.errors['_ref_node_id'],
            # TODO: This could be any other message, so if
            # there's a default like This field is required then that's fine too.
            ['You must specify a relative menu item']
        )

    def test_invalid_if_no_relative_node_specified_and_left_position(self):
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": 0,
            "numchild": 1,
            "link_target": "_self",
            "_position": "left",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn('_ref_node_id', form.errors)
        self.assertListEqual(
            form.errors['_ref_node_id'],
            # TODO: This could be any other message, so if
            # there's a default like This field is required then that's fine too.
            ['You must specify a relative menu item']
        )

    def test_invalid_if_no_relative_node_specified_and_right_position(self):
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": 0,
            "numchild": 1,
            "link_target": "_self",
            "_position": "right",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn('_ref_node_id', form.errors)
        self.assertListEqual(
            form.errors['_ref_node_id'],
            # TODO: This could be any other message, so if
            # there's a default like This field is required then that's fine too.
            ['You must specify a relative menu item']
        )

    def test_invalid_if_trying_to_add_right_sibling_of_existing_root_node(self):
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": self.menu_root.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "right",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn('_ref_node_id', form.errors)
        self.assertListEqual(
            form.errors['_ref_node_id'],
            # TODO: This could be any other message, so if
            # there's some other default then that's fine too.
            ['You cannot add a sibling for this menu item']
        )

    def test_invalid_if_trying_to_add_left_sibling_of_existing_root_node(self):
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": self.menu_root.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "left",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn('_ref_node_id', form.errors)
        self.assertListEqual(
            form.errors['_ref_node_id'],
            # TODO: This could be any other message, so if
            # there's some other default then that's fine too.
            ['You cannot add a sibling for this menu item']
        )

    def test_doesnt_throw_500_errors_if_ref_node_id_missing_from_post(self):
        data = {
            "title": "Armadillos",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        try:
            form.is_valid()
        except Exception as e:
            self.fail("Should display a form error, not %s" % str(e))

    def test_only_display_node_tree_of_current_root(self):
        child = factories.ChildMenuItemFactory(parent=self.menu_root)
        root2 = factories.RootMenuItemFactory()
        child_of_root2 = factories.ChildMenuItemFactory(parent=root2)
        form = MenuItemForm(menu_root=self.menu_root)

        menu_item_ids = [
            choice[0] for choice in form.declared_fields['_ref_node_id'].choices]

        # The menu items that should be in choices are indeed there
        self.assertIn(self.menu_root.pk, menu_item_ids)
        self.assertIn(child.pk, menu_item_ids)
        # Those from other root nodes are not
        self.assertNotIn(root2.pk, menu_item_ids)
        self.assertNotIn(child_of_root2.pk, menu_item_ids)
        # And the general count is correct
        # TODO: If --root-- is removed then this should be 4 not 5
        self.assertEqual(len(form.declared_fields['_ref_node_id'].choices), 5)

    def test_do_not_display_root_option_in_relative_field(self):
        form = MenuItemForm(menu_root=self.menu_root)
        menu_item_ids = [
            choice[0] for choice in form.declared_fields['_ref_node_id'].choices]
        self.assertNotIn(0, menu_item_ids)
