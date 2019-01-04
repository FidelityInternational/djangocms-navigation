from django.conf.urls import url
from django.contrib import admin
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import reverse, HttpResponseRedirect
from django.utils.text import slugify
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory, _get_exclude_for_model
from .models import Menu, MenuContent, MenuItem


class MenuContentAdmin(admin.ModelAdmin):
    exclude = ["menu"]
    list_display = ["title", "get_menuitem_link"]

    def save_model(self, request, obj, form, change):
        if not change:
            # Creating grouper object for menu content
            obj.menu = Menu.objects.create(
                identifier=slugify(obj.title), site=get_current_site(request)
            )
        super().save_model(request, obj, form, change)

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
    form = movenodeform_factory(
        MenuItem, exclude=_get_exclude_for_model(MenuItem, ['menu_content']))
    change_list_template = "/admin/djangocms_navigation/menuitem/change_list.html"

    def save_form(self, request, form, change):
        if not change:
            form.cleaned_data['menu_content_id'] = request.menu_content_id
        return super().save_form(request, form, change)

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            url(
                r"^(?P<menu_content_id>\d+)/list/",
                self.admin_site.admin_view(self.changelist_view),
                name="{}_{}_list".format(*info),
            ),
            url(
                r"^(?P<menu_content_id>\d+)/add/",
                self.admin_site.admin_view(self.add_view),
                name="{}_{}_add".format(*info),
            ),
        ] + super().get_urls()

    def get_queryset(self, request):
        if hasattr(request, "menu_content_id"):
            return MenuItem.objects.filter(menu_content=request.menu_content_id)
        return self.model().get_tree()

    def add_view(self, request, menu_content_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if menu_content_id:
            request.menu_content_id = menu_content_id
        return super().add_view(request, form_url=form_url, extra_context=extra_context)

    def changelist_view(self, request, menu_content_id=None, extra_context=None):
        extra_context = extra_context or {}

        if menu_content_id:
            request.menu_content_id = menu_content_id
            extra_context["menu_content_id"] = request.menu_content_id
            extra_context["add_url"] = reverse(
                "admin:djangocms_navigation_menuitem_add",
                kwargs={"menu_content_id": request.menu_content_id},
            )

        return super().changelist_view(request, extra_context)

    def response_change(self, request, obj):
        url = reverse(
            "admin:djangocms_navigation_menuitem_list",
            kwargs={"menu_content_id": getattr(request, "menu_content_id", 0)},
        )
        return HttpResponseRedirect(url)

    def response_add(self, request, obj, post_url_continue=None):
        url = reverse(
            "admin:djangocms_navigation_menuitem_list",
            kwargs={"menu_content_id": request.menu_content_id},
        )
        return HttpResponseRedirect(url)


admin.site.register(MenuItem, MenuItemAdmin)
admin.site.register(MenuContent, MenuContentAdmin)
