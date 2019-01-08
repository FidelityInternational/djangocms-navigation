from django.test import TestCase
from django.test import RequestFactory
from cms.test_utils.testcases import CMSTestCase

from djangocms_navigation.models import Menu, MenuContent, MenuItem
from djangocms_navigation.test_utils import factories
from djangocms_navigation.admin import MenuContentAdmin
from djangocms_navigation.forms import MenuContentForm


class MenuContentModelTestCase(CMSTestCase):

    def test_title(self):
        menu_content = factories.MenuContentFactory(root__title="My Title")
        self.assertEqual(menu_content.title, "My Title")

    # def test_grouper_menu_created(self):
    #     # request = RequestFactory()
    #     # request.user = self.get_superuser()
    #     # form = MenuContentForm(data={"title": "My Title"})
    #     # change = False
    #     # menu_content = MenuContentAdmin.save_model(request, obj, form, change)
    #     # self.assertIsInstance(menu_content.menu, Menu)
    #     form_data = {'title': 'something'}
    #     form = MenuContentForm(data=form_data)
    #     form.save(commit=True)
    #     import pdb; pdb.set_trace()
    # # def test_root_menuitem_created(self):
    #     menu_content = MenuContent.objects.create(root__title="My Title")
    #     self.assertIsInstance(menu_content.root, MenuItem)
    #
    # def test_string_representation(self):
    #     menu_content = MenuContent.objects.create(root__title="My Title")
    #     self.assertEqual(str(menu_content), menu_content.title)
