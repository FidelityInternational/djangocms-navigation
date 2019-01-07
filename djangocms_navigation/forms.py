from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from treebeard.forms import MoveNodeForm, _get_exclude_for_model
from .models import NavigationPlugin, MenuItem, MenuContent
from .utils import supported_models


class NavigationPluginForm(forms.ModelForm):
    class Meta:
        model = NavigationPlugin
        fields = ("template",)


class Select2Mixin:
    class Media:
        css = {"all": ("cms/js/select2/select2.css",)}
        js = ("cms/js/select2/select2.js", "djangocms_url_manager/js/create_url.js")


class UrlSelectWidget(Select2Mixin, forms.Select):
    pass


class UrlTypeSelectWidget(Select2Mixin, forms.Select):
    pass


class MenuContentForm(forms.ModelForm):
    title = forms.CharField(label="Menu Title", max_length=100)

    class Meta:
        model = MenuContent
        fields = ["title"]


class MenuItemForm(MoveNodeForm):
    content_type = forms.ChoiceField(
        label=_("Content Type"),
        widget=UrlTypeSelectWidget(
            attrs={"data-placeholder": _("Select Content Type")}
        ),
    )

    object_id = forms.ChoiceField(
        label=_("Content"),
        widget=UrlTypeSelectWidget(attrs={"data-placeholder": _("Select Page")}),
    )

    class Meta:
        model = MenuItem
        exclude = _get_exclude_for_model(model, None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        choices = []
        content_choices = []
        for model in supported_models():
            choices.append(
                (
                    ContentType.objects.get_for_model(model).id,
                    model._meta.verbose_name.capitalize(),
                )
            )

            content_choices.extend([(obj.id, obj) for obj in model.objects.all()])

        self.fields["content_type"].choices = choices
        self.fields["object_id"].choices = content_choices

        if self.instance:

            if self.instance.content_type_id:
                self.fields["content_type"].initial = self.instance.content_type
                self.fields["object_id"].initial = self.instance.object_id

    def clean(self):
        data = super().clean()
        data["content_type"] = ContentType.objects.get(id=data["content_type"])
        return data

    def save(self, **kwargs):
        self.instance.object_id = self.cleaned_data["object_id"]
        self.instance.content_type = self.cleaned_data["content_type"]
        return super().save(**kwargs)
