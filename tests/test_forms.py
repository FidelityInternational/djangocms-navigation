from cms.models import Page
from cms.test_utils.testcases import CMSTestCase

from django.contrib.contenttypes.models import ContentType

from djangocms_navigation.forms import MenuItemForm
from djangocms_navigation.test_utils import factories
from djangocms_navigation.test_utils.app_1.models import TestModel1, TestModel2
from djangocms_navigation.test_utils.app_2.models import TestModel3, TestModel4


class MenuContentFormTestCase(CMSTestCase):

    def setUp(self):
        self.menu_root = factories.RootMenuItemFactory()
        self.page_content = factories.PageContentFactory()
        self.page_ct = ContentType.objects.get_for_model(Page)

    def test_valid_if_adding_child_of_existing_root_node(self):
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": self.menu_root.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_valid_if_adding_child_of_existing_child_node(self):
        item = factories.ChildMenuItemFactory(parent=self.menu_root)
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": item.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_valid_if_adding_right_sibling_of_existing_child_node(self):
        item = factories.ChildMenuItemFactory(parent=self.menu_root)
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": item.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "right",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_valid_if_adding_left_sibling_of_existing_child_node(self):
        item = factories.ChildMenuItemFactory(parent=self.menu_root)
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": item.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "left",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_valid_if_changing_existing_root_node(self):
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": 0,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(
            menu_root=self.menu_root, data=data, instance=self.menu_root
        )

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_valid_if_changing_existing_child_node(self):
        item = factories.ChildMenuItemFactory(parent=self.menu_root)
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": item.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data, instance=item)

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_invalid_if_no_relative_node_specified_and_child_position(self):
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": 0,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn("_ref_node_id", form.errors)
        self.assertListEqual(
            form.errors["_ref_node_id"],
            ["You must specify a relative menu item"],
        )

    def test_invalid_if_no_relative_node_specified_and_left_position(self):
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": 0,
            "numchild": 1,
            "link_target": "_self",
            "_position": "left",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn("_ref_node_id", form.errors)
        self.assertListEqual(
            form.errors["_ref_node_id"],
            ["You must specify a relative menu item"],
        )

    def test_invalid_if_no_relative_node_specified_and_right_position(self):
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": 0,
            "numchild": 1,
            "link_target": "_self",
            "_position": "right",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn("_ref_node_id", form.errors)
        self.assertListEqual(
            form.errors["_ref_node_id"],
            ["You must specify a relative menu item"],
        )

    def test_invalid_if_trying_to_add_right_sibling_of_existing_root_node(self):
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": self.menu_root.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "right",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn("_ref_node_id", form.errors)
        self.assertListEqual(
            form.errors["_ref_node_id"],
            ["You cannot add a sibling for this menu item"],
        )

    def test_invalid_if_trying_to_add_left_sibling_of_existing_root_node(self):
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": self.menu_root.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "left",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn("_ref_node_id", form.errors)
        self.assertListEqual(
            form.errors["_ref_node_id"],
            ["You cannot add a sibling for this menu item"],
        )

    def test_invalid_if_relative_node_id_points_to_non_existing_node(self):
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": 167,  # node does not exist
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn("_ref_node_id", form.errors)
        self.assertListEqual(
            form.errors["_ref_node_id"],
            ["Select a valid choice. 167 is not one of the available choices."],
        )

    def test_title_is_required(self):
        data = {
            "title": "",
            "content_type": self.page_ct.pk,
            "object_id": self.page_content.page.pk,
            "_ref_node_id": self.menu_root.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn('title', form.errors)
        self.assertIn('This field is required.', form.errors['title'])

    def test_content_type_is_optional(self):
        data = {
            "title": "My new Title",
            "object_id": self.page_content.page.pk,
            "_ref_node_id": self.menu_root.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_object_id_is_optional(self):
        data = {
            "title": "My new Title",
            "content_type": self.page_ct.pk,
            "_ref_node_id": self.menu_root.id,
            "numchild": 1,
            "link_target": "_self",
            "_position": "first-child",
        }
        form = MenuItemForm(menu_root=self.menu_root, data=data)

        is_valid = form.is_valid()

        self.assertTrue(is_valid)

    def test_doesnt_throw_500_errors_if_data_missing_from_post(self):
        form = MenuItemForm(menu_root=self.menu_root, data={})
        try:
            form.is_valid()
        except Exception as e:
            self.fail(str(e))

    def test_only_display_node_tree_of_current_root(self):
        child = factories.ChildMenuItemFactory(parent=self.menu_root)
        root2 = factories.RootMenuItemFactory()
        child_of_root2 = factories.ChildMenuItemFactory(parent=root2)
        form = MenuItemForm(menu_root=self.menu_root)

        menu_item_ids = [
            choice[0] for choice in form.fields["_ref_node_id"].choices
        ]

        # The menu items that should be in choices are indeed there
        self.assertIn(self.menu_root.pk, menu_item_ids)
        self.assertIn(child.pk, menu_item_ids)
        # Those from other root nodes are not
        self.assertNotIn(root2.pk, menu_item_ids)
        self.assertNotIn(child_of_root2.pk, menu_item_ids)
        # And the general count is correct
        self.assertEqual(len(form.fields["_ref_node_id"].choices), 3)

    def test_only_display_supported_content_types(self):
        content_types = ContentType.objects.get_for_models(
            Page, TestModel1, TestModel2, TestModel3, TestModel4)
        form = MenuItemForm(menu_root=self.menu_root)

        queryset = form.fields['content_type'].queryset

        expected_content_type_pks = [ct.pk for ct in content_types.values()]
        self.assertQuerysetEqual(queryset, expected_content_type_pks, lambda o: o.pk, ordered=False)
