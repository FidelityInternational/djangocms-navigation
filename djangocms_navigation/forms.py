from django import forms
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from cms.utils.urlutils import admin_reverse

from treebeard.forms import MoveNodeForm, _get_exclude_for_model

from .constants import MENU_MODEL, ITEM_MODEL
from .models import NavigationPlugin
from .utils import supported_content_type_pks, get_model, get_select2_url_name

MenuContent = get_model(MENU_MODEL)
MenuItem = get_model(ITEM_MODEL)


class NavigationPluginForm(forms.ModelForm):
    class Meta:
        model = NavigationPlugin
        fields = ("template", "menu")


class MenuContentForm(forms.ModelForm):
    title = forms.CharField(label=_("Menu Title"), max_length=100)

    class Meta:
        model = MenuContent
        fields = ["title"]


class Select2Mixin:
    class Media:
        css = {"all": ("cms/js/select2/select2.css",)}
        js = ("cms/js/select2/select2.js", "djangocms_navigation/js/create_url.js")


class ContentTypeObjectSelectWidget(Select2Mixin, forms.TextInput):
    def get_url(self):
        return admin_reverse(get_select2_url_name())

    def build_attrs(self, *args, **kwargs):
        attrs = super().build_attrs(*args, **kwargs)
        attrs.setdefault("data-select2-url", self.get_url())
        return attrs


class MenuItemForm(MoveNodeForm):

    object_id = forms.CharField(
        label=_("Content Object"),
        widget=ContentTypeObjectSelectWidget(
            attrs={"data-placeholder": _("Select content object")}
        ),
        required=False,
    )

    class Meta:
        model = MenuItem
        exclude = _get_exclude_for_model(model, None)

    def __init__(self, *args, **kwargs):
        self.menu_root = kwargs.pop("menu_root")
        super().__init__(*args, **kwargs)

        self.fields["content_type"].queryset = self.fields[
            "content_type"
        ].queryset.filter(pk__in=supported_content_type_pks())

        self.fields["_ref_node_id"].choices = self.mk_dropdown_tree(
            MenuItem, for_node=self.menu_root.get_root()
        )

    def clean(self):
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data

        object_id = cleaned_data.get("object_id")
        content_type = cleaned_data.get("content_type")
        _ref_node_id = cleaned_data.get("_ref_node_id")
        _position = cleaned_data.get("_position")

        if not object_id:
            cleaned_data["object_id"] = None

        Model = self._meta.model
        try:
            node = Model.objects.get(id=_ref_node_id)
        except Model.DoesNotExist:
            node = None

        # Check we're not trying to modify the root node cause some
        # validation will not apply
        changing_root = self.instance.pk and self.instance.is_root()
        if not node and not changing_root:
            raise forms.ValidationError(
                {"_ref_node_id": _("You must specify a relative menu item")}
            )

        if node and node.is_root() and _position in ["left", "right"]:
            raise forms.ValidationError(
                {"_ref_node_id": [_("You cannot add a sibling for this menu item")]}
            )

        if self.instance and not self.instance.is_root() and content_type and object_id:
            try:
                obj = content_type.model_class().objects.get(
                    pk=object_id
                )  # flake8: noqa
            except content_type.model_class().DoesNotExist:
                raise forms.ValidationError({"object_id": [_("Invalid object")]})

        if content_type and not object_id:
            raise forms.ValidationError({"object_id": [_("Please select content object")]})

        if not content_type and object_id:
            raise forms.ValidationError(
                {"content_type": [_("Please select content type")]}
            )

        return cleaned_data

    @classmethod
    def mk_dropdown_tree(cls, model, for_node=None):
        """ Creates a tree-like list of choices for root node """
        options = [(0, _("-- root --"))]
        if for_node:
            for node in model.get_tree(for_node):
                options.append(
                    (node.pk, mark_safe(cls.mk_indent(node.get_depth()) + escape(node)))
                )
        return options
