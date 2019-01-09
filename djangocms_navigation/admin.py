from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.exceptions import DisallowedModelAdminToField
from django.contrib.admin.options import TO_FIELD_VAR, IS_POPUP_VAR
from django.contrib.admin.utils import quote, unquote
from django.contrib.admin.views.main import ChangeList
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied
from django.forms.formsets import all_valid
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import reverse
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.views.i18n import JavaScriptCatalog

from treebeard.admin import TreeAdmin

from .forms import MenuContentForm, MenuItemForm
from .models import Menu, MenuContent, MenuItem


class MenuItemChangeList(ChangeList):
    def __init__(self, request, *args, **kwargs):
        self.menu_content_id = request.menu_content_id
        super().__init__(request, *args, **kwargs)

    def url_for_result(self, result):
        pk = getattr(result, self.pk_attname)
        return reverse(
            "admin:%s_%s_change" % (self.opts.app_label, self.opts.model_name),
            args=(self.menu_content_id, quote(pk)),
            current_app=self.model_admin.admin_site.name,
        )


class MenuContentAdmin(admin.ModelAdmin):
    form = MenuContentForm
    list_display = ["title", "get_menuitem_link"]
    list_display_links = None

    def save_model(self, request, obj, form, change):
        if not change:
            title = form.cleaned_data.get("title")
            # Creating grouper object for menu content
            obj.menu = Menu.objects.create(
                identifier=slugify(title), site=get_current_site(request)
            )
            # Creating root menu item with title
            obj.root = MenuItem.add_root(title=title)
        super().save_model(request, obj, form, change)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        meta = MenuItem._meta
        return HttpResponseRedirect(
            reverse(
                "admin:{app}_{model}_list".format(
                    app=meta.app_label, model=meta.model_name
                ),
                args=[object_id],
            )
        )

    def get_menuitem_link(self, obj):
        object_preview_url = reverse(
            "admin:{app}_{model}_list".format(
                app=obj._meta.app_label, model=MenuItem._meta.model_name
            ),
            args=[obj.pk],
        )

        return format_html(
            '<a href="{}" class="js-moderation-close-sideframe" target="_top">'
            '<span class="cms-icon cms-icon-eye"></span> {}'
            "</a>",
            object_preview_url,
            _("Items"),
        )

    get_menuitem_link.short_description = _("Menu Items")


class MenuItemAdmin(TreeAdmin):
    form = MenuItemForm
    change_list_template = "admin/djangocms_navigation/menuitem/change_list.html"

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            url(
                r"^(?P<menu_content_id>\d+)/$",
                self.admin_site.admin_view(self.changelist_view),
                name="{}_{}_list".format(*info),
            ),
            url(
                r"^(?P<menu_content_id>\d+)/add/$",
                self.admin_site.admin_view(self.add_view),
                name="{}_{}_add".format(*info),
            ),
            url(
                r"^(?P<menu_content_id>\d+)/(?P<object_id>\d+)/change/$",
                self.admin_site.admin_view(self.change_view),
                name="{}_{}_change".format(*info),
            ),
            url(
                r"^(?P<menu_content_id>\d+)/move/$",
                self.admin_site.admin_view(self.move_node),
            ),
            url(
                r"^(?P<menu_content_id>\d+)/jsi18n/$",
                JavaScriptCatalog.as_view(packages=["treebeard"]),
            ),
        ]

    def get_queryset(self, request):
        if hasattr(request, "menu_content_id"):
            menu_content = MenuContent._base_manager.get(id=request.menu_content_id)
            return MenuItem.get_tree(menu_content.root)
        return self.model().get_tree()

    def change_view(
        self, request, object_id, menu_content_id=None, form_url="", extra_context=None
    ):
        extra_context = extra_context or {}
        if menu_content_id:
            request.menu_content_id = menu_content_id
            extra_context["list_url"] = reverse(
                "admin:djangocms_navigation_menuitem_list",
                kwargs={"menu_content_id": menu_content_id},
            )
        return super().change_view(
            request, object_id, form_url="", extra_context=extra_context
        )

    def add_view(self, request, menu_content_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if menu_content_id:
            request.menu_content_id = menu_content_id
            extra_context["list_url"] = reverse(
                "admin:djangocms_navigation_menuitem_list",
                kwargs={"menu_content_id": menu_content_id},
            )
        return super().add_view(request, form_url=form_url, extra_context=extra_context)

    def _changeform_view(self, request, object_id, form_url, extra_context):
        """Overridden because unlike later versions of django, 1.11 doesn't
        have a way to easily add additional form kwargs when instantiating
        a form"""
        to_field = request.POST.get(TO_FIELD_VAR, request.GET.get(TO_FIELD_VAR))
        if to_field and not self.to_field_allowed(request, to_field):
            raise DisallowedModelAdminToField("The field %s cannot be referenced." % to_field)

        model = self.model
        opts = model._meta

        if request.method == 'POST' and '_saveasnew' in request.POST:
            object_id = None

        add = object_id is None

        if add:
            if not self.has_add_permission(request):
                raise PermissionDenied
            obj = None

        else:
            obj = self.get_object(request, unquote(object_id), to_field)

            if not self.has_change_permission(request, obj):
                raise PermissionDenied

            if obj is None:
                return self._get_obj_does_not_exist_redirect(request, opts, object_id)

        ModelForm = self.get_form(request, obj)
        if request.method == 'POST':
            menu_root = MenuContent._base_manager.get(id=request.menu_content_id).root
            form = ModelForm(
                request.POST, request.FILES, instance=obj, menu_root=menu_root)
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=not add)
            else:
                form_validated = False
                new_object = form.instance
            formsets, inline_instances = self._create_formsets(request, new_object, change=not add)
            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, not add)
                self.save_related(request, form, formsets, not add)
                change_message = self.construct_change_message(request, form, formsets, add)
                if add:
                    self.log_addition(request, new_object, change_message)
                    return self.response_add(request, new_object)
                else:
                    self.log_change(request, new_object, change_message)
                    return self.response_change(request, new_object)
            else:
                form_validated = False
        else:
            if add:
                initial = self.get_changeform_initial_data(request)
                form = ModelForm(initial=initial)
                formsets, inline_instances = self._create_formsets(request, form.instance, change=False)
            else:
                form = ModelForm(instance=obj)
                formsets, inline_instances = self._create_formsets(request, obj, change=True)

        adminForm = helpers.AdminForm(
            form,
            list(self.get_fieldsets(request, obj)),
            self.get_prepopulated_fields(request, obj),
            self.get_readonly_fields(request, obj),
            model_admin=self)
        media = self.media + adminForm.media

        inline_formsets = self.get_inline_formsets(request, formsets, inline_instances, obj)
        for inline_formset in inline_formsets:
            media = media + inline_formset.media

        context = dict(
            self.admin_site.each_context(request),
            title=(_('Add %s') if add else _('Change %s')) % force_text(opts.verbose_name),
            adminform=adminForm,
            object_id=object_id,
            original=obj,
            is_popup=(IS_POPUP_VAR in request.POST or
                      IS_POPUP_VAR in request.GET),
            to_field=to_field,
            media=media,
            inline_admin_formsets=inline_formsets,
            errors=helpers.AdminErrorList(form, formsets),
            preserved_filters=self.get_preserved_filters(request),
        )

        # Hide the "Save" and "Save and continue" buttons if "Save as New" was
        # previously chosen to prevent the interface from getting confusing.
        if request.method == 'POST' and not form_validated and "_saveasnew" in request.POST:
            context['show_save'] = False
            context['show_save_and_continue'] = False
            # Use the change template instead of the add template.
            add = False

        context.update(extra_context or {})

        return self.render_change_form(request, context, add=add, change=not add, obj=obj, form_url=form_url)

    def changelist_view(self, request, menu_content_id=None, extra_context=None):
        extra_context = extra_context or {}

        if menu_content_id:
            request.menu_content_id = menu_content_id
            extra_context["add_url"] = reverse(
                "admin:djangocms_navigation_menuitem_add",
                kwargs={"menu_content_id": menu_content_id},
            )
            extra_context["list_url"] = reverse(
                "admin:djangocms_navigation_menuitem_list",
                kwargs={"menu_content_id": menu_content_id},
            )

        return super().changelist_view(request, extra_context)

    def response_change(self, request, obj):
        url = reverse(
            "admin:djangocms_navigation_menuitem_list",
            kwargs={"menu_content_id": request.menu_content_id},
        )
        return HttpResponseRedirect(url)

    def response_add(self, request, obj, post_url_continue=None):
        url = reverse(
            "admin:djangocms_navigation_menuitem_list",
            kwargs={"menu_content_id": request.menu_content_id},
        )
        return HttpResponseRedirect(url)

    def move_node(self, request, menu_content_id):
        if request.POST.get("parent_id") == "0":
            message = _("Cannot move a node outside of root menu node")
            messages.error(request, message)
            return HttpResponseBadRequest(message)
        return super().move_node(request)

    def has_add_permission(self, request):
        if not hasattr(request, "menu_content_id"):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if not hasattr(request, "menu_content_id"):
            return False
        return super().has_change_permission(request, obj)

    def get_changelist(self, request, **kwargs):
        return MenuItemChangeList

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        menu_root = MenuContent.objects.get(id=request.menu_content_id).root

        class Form(form_class):
            def __new__(cls, *args, **kwargs):
                kwargs["menu_root"] = menu_root
                return form_class(*args, **kwargs)

        return Form


admin.site.register(MenuItem, MenuItemAdmin)
admin.site.register(MenuContent, MenuContentAdmin)
