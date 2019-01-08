from cms.test_utils.testcases import CMSTestCase

from djangocms_navigation.forms import MenuItemForm


class MenuContentFormTestCase(CMSTestCase):
    # Todo: add more test while change object field to autocomplete

    def test_menuitemformcontent(self):
        data = {
            "title": "My new Title",
            "content_type": 1,
            "object_id": 1,
            "_ref_node_id": 0,
            "numchild": 1,
            "link_targe": "_self",
        }
        form = MenuItemForm(data)
        self.assertFalse(form.is_valid())
