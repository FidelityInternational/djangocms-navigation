from django import forms
from treebeard.forms import MoveNodeForm, _get_exclude_for_model
from .models import NavigationPlugin, MenuItem, MenuContent


class NavigationPluginForm(forms.ModelForm):
    class Meta:
        model = NavigationPlugin
        fields = ("template",)


class MenuItemForm(MoveNodeForm):
    class Meta:
        model = MenuItem
        exclude = _get_exclude_for_model(model, ("menu_content",))
