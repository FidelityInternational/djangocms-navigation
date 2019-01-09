from cms.test_utils.testcases import CMSTestCase

from djangocms_navigation.forms import MenuItemForm
from djangocms_navigation.test_utils import factories


class MenuContentFormTestCase(CMSTestCase):
    # Todo: add more test while change object field to autocomplete

    def test_valid(self):
        item = factories.RootMenuItemFactory()
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": item.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(data)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_invalid_if_trying_to_add_root_node(self):
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": 0,
            "numchild": 1,
            "link_target": "_self",
            "_position": "right",
        }
        form = MenuItemForm(data)
        # Hack the form so there's a valid choice for object_id
        # TODO: This will need to be modified when autocomplete is added
        form.fields['object_id'].choices = [(1, 'Object')]

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn('__all__', form.errors)
        self.assertListEqual(
            form.errors['__all__'],
            ['Adding root menuitem is not allowed']
        )

    def test_invalid_if_trying_to_add_child_of_non_existing_root_node(self):
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": 0,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(data)
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
        item = factories.RootMenuItemFactory()
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": item.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "right",
        }
        form = MenuItemForm(data)
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
        item = factories.RootMenuItemFactory()
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": item.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "left",
        }
        form = MenuItemForm(data)
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
