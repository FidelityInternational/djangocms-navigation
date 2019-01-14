import string

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

from cms.models import Page, PageContent, TreeNode

import factory
from djangocms_versioning.models import Version
from factory.fuzzy import FuzzyChoice, FuzzyInteger, FuzzyText

from ..models import Menu, MenuContent, MenuItem


class UserFactory(factory.django.DjangoModelFactory):
    username = FuzzyText(length=12)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.LazyAttribute(
        lambda u: "%s.%s@example.com" % (u.first_name.lower(), u.last_name.lower())
    )

    class Meta:
        model = User

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default ``_create`` with our custom call."""
        manager = cls._get_manager(model_class)
        # The default would use ``manager.create(*args, **kwargs)``
        return manager.create_user(*args, **kwargs)


class AbstractVersionFactory(factory.DjangoModelFactory):
    object_id = factory.SelfAttribute("content.id")
    content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(o.content)
    )
    created_by = factory.SubFactory(UserFactory)

    class Meta:
        exclude = ["content"]
        abstract = True


class TreeNodeFactory(factory.django.DjangoModelFactory):
    site = factory.fuzzy.FuzzyChoice(Site.objects.all())
    depth = 0
    # NOTE: Generating path this way is probably not a good way of
    # doing it, but seems to work for our present tests which only
    # really need a tree node to exist and not throw unique constraint
    # errors on this field. If the data in this model starts mattering
    # in our tests then something more will need to be done here.
    path = FuzzyText(length=8, chars=string.digits)

    class Meta:
        model = TreeNode


class PageFactory(factory.django.DjangoModelFactory):
    node = factory.SubFactory(TreeNodeFactory)

    class Meta:
        model = Page


class PageContentFactory(factory.django.DjangoModelFactory):
    page = factory.SubFactory(PageFactory)
    language = FuzzyChoice(["en", "fr", "it"])
    title = FuzzyText(length=12)
    page_title = FuzzyText(length=12)
    menu_title = FuzzyText(length=12)
    meta_description = FuzzyText(length=12)
    redirect = FuzzyText(length=12)
    created_by = FuzzyText(length=12)
    changed_by = FuzzyText(length=12)
    in_navigation = FuzzyChoice([True, False])
    soft_root = FuzzyChoice([True, False])
    template = FuzzyText(length=12)
    limit_visibility_in_menu = FuzzyInteger(0, 25)
    xframe_options = FuzzyInteger(0, 25)

    class Meta:
        model = PageContent


class PageVersionFactory(AbstractVersionFactory):
    content = factory.SubFactory(PageContentFactory)

    class Meta:
        model = Version


class PageContentWithVersionFactory(PageContentFactory):
    @factory.post_generation
    def version(self, create, extracted, **kwargs):
        # NOTE: Use this method as below to define version attributes:
        # PollContentWithVersionFactory(version__label='label1')
        if not create:
            # Simple build, do nothing.
            return
        PageVersionFactory(content=self, **kwargs)


class MenuFactory(factory.django.DjangoModelFactory):
    identifier = FuzzyText(length=6)
    site = factory.fuzzy.FuzzyChoice(Site.objects.all())

    class Meta:
        model = Menu


class MenuItemFactory(factory.django.DjangoModelFactory):
    """Abstract factory to use as a base for other factories that
    set the path and depth attributes sensibly for root, child and
    sibling nodes."""

    title = FuzzyText(length=24)
    object_id = factory.SelfAttribute("content.id")
    content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(o.content)
    )
    content = factory.SubFactory(PageContentWithVersionFactory)

    class Meta:
        model = MenuItem
        abstract = True


class RootMenuItemFactory(MenuItemFactory):
    object_id = None
    content_type = None
    content = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Make sure this is the root of a tree"""
        return model_class.add_root(*args, **kwargs)


class ChildMenuItemFactory(MenuItemFactory):
    # A child node needs to have a parent node. This will automatically
    # generate the parent, but you can also supply your own.
    parent = factory.SubFactory(RootMenuItemFactory)

    class Meta:
        model = MenuItem
        inline_args = ("parent",)

    @classmethod
    def _create(cls, model_class, parent, *args, **kwargs):
        """Make sure this is the child of a parent node"""
        return parent.add_child(*args, **kwargs)


class SiblingMenuItemFactory(MenuItemFactory):
    # A sibling node needs to have a sibling node of course.
    # This will automatically generate a new child node as the sibling,
    # but you can also supply an existing node with the sibling arg.
    sibling = factory.SubFactory(ChildMenuItemFactory)
    # Siblings need to be positioned against their sibling nodes.
    # A position will be randomly chosen from this list or you can
    # supply your own with the position arg.
    _SIBLING_POSITIONS = [
        'first-sibling',
        'left',
        'right',
        'last-sibling',
    ]
    position = FuzzyChoice(_SIBLING_POSITIONS)

    class Meta:
        model = MenuItem
        inline_args = ('sibling', 'position')

    @classmethod
    def _create(cls, model_class, sibling, position, *args, **kwargs):
        """Make sure this is the sibling of the supplied node"""
        return sibling.add_sibling(pos=position, **kwargs)


class MenuContentFactory(factory.django.DjangoModelFactory):
    menu = factory.SubFactory(MenuFactory)
    root = factory.SubFactory(RootMenuItemFactory)

    class Meta:
        model = MenuContent


class MenuVersionFactory(AbstractVersionFactory):
    content = factory.SubFactory(MenuContentFactory)

    class Meta:
        model = Version
