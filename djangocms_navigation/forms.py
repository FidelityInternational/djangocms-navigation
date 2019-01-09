from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from treebeard.forms import MoveNodeForm, _get_exclude_for_model

from .models import MenuContent, MenuItem, NavigationPlugin
from .utils import supported_models


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
    content_type = forms.ModelChoiceField(
        label=_("Content Type"), queryset=ContentType.objects.all()
    )

    # Todo: use autocomplete to select page object
    object_id = forms.ChoiceField(
        label=_("Content"),
        widget=forms.Select(attrs={"data-placeholder": _("Select Page")}),
    )

    class Meta:
        model = MenuItem
        exclude = _get_exclude_for_model(model, None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        opts = self._meta
        menu_root = MenuContent.objects.get(id=self.request.menu_content_id).root

        # Todo: optimisation
        content_choices = []
        for model in supported_models():
            content_choices.extend([(obj.id, obj) for obj in model.objects.all()])

        self.fields["object_id"].choices = content_choices

        node_choices = self.mk_dropdown_tree(opts.model, for_node=menu_root.get_root())
        self.fields["_ref_node_id"].choices = node_choices
        if self.instance:
            self.fields["object_id"].initial = self.instance.object_id

    def clean(self):
        data = super().clean()
        try:
            node = MenuItem.objects.get(id=data["_ref_node_id"])
        except MenuItem.DoesNotExist:
            node = None

        if not node:
            raise forms.ValidationError(
                {"_ref_node_id": "You must specify a relative menu item"}
            )

        if data["_ref_node_id"] == 0:
            raise forms.ValidationError("Adding root menuitem is not allowed")

        if node.is_root() and data["_position"] in ["left", "right"]:
            raise forms.ValidationError(
                {"_ref_node_id": ["You cannot add a sibling for this menu item"]}
            )

        return data

    def save(self, **kwargs):
        self.instance.object_id = self.cleaned_data["object_id"]
        self.instance.content_type = self.cleaned_data["content_type"]
        return super().save(**kwargs)

    @classmethod
    def mk_dropdown_tree(cls, model, for_node=None):
        """ Creates a tree-like list of choices for root node """
        options = [(0, _("-- root --"))]
        for node in for_node.get_descendants():
            options.append(
                (node.pk, mark_safe(cls.mk_indent(node.get_depth()) + escape(node)))
            )
        return options
