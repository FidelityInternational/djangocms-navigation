from django import forms
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from treebeard.forms import MoveNodeForm, _get_exclude_for_model

from .models import MenuContent, MenuItem, NavigationPlugin
from .utils import supported_content_type_pks, supported_models


class NavigationPluginForm(forms.ModelForm):
    class Meta:
        model = NavigationPlugin
        fields = ("template",)


class MenuContentForm(forms.ModelForm):
    title = forms.CharField(label=_("Menu Title"), max_length=100)

    class Meta:
        model = MenuContent
        fields = ["title"]


class MenuItemForm(MoveNodeForm):
    # Todo: use autocomplete to select page object

    class Meta:
        model = MenuItem
        exclude = _get_exclude_for_model(model, None)

    def __init__(self, *args, **kwargs):
        self.menu_root = kwargs.pop("menu_root")
        super().__init__(*args, **kwargs)

        self.fields['object_id'].widget = forms.Select(
            attrs={"data-placeholder": _("Select Page")})
        self.fields['object_id'].label = ("Content")

        self.fields["content_type"].queryset = self.fields[
            "content_type"].queryset.filter(pk__in=supported_content_type_pks())

        self.fields["_ref_node_id"].choices = self.mk_dropdown_tree(
            MenuItem, for_node=self.menu_root.get_root()
        )

        # Todo: change when autocomplete implemented, tests for this field
        content_choices = []
        for model in supported_models():
            content_choices.extend([(obj.id, obj) for obj in model.objects.all()])
        self.fields["object_id"].choices = content_choices

        # TODO: If this initial still needed after autocomplete changes
        # then don't forget to write tests for this
        if self.instance:
            self.fields["object_id"].initial = self.instance.object_id

    def clean(self):
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data

        try:
            node = MenuItem.objects.get(id=cleaned_data["_ref_node_id"])
        except MenuItem.DoesNotExist:
            node = None

        # Check we're not trying to modify the root node cause some
        # validation will not apply
        changing_root = self.instance.pk and self.instance.is_root()
        if not node and not changing_root:
            raise forms.ValidationError(
                {"_ref_node_id": "You must specify a relative menu item"}
            )

        if node and node.is_root() and cleaned_data["_position"] in ["left", "right"]:
            raise forms.ValidationError(
                {"_ref_node_id": ["You cannot add a sibling for this menu item"]}
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
