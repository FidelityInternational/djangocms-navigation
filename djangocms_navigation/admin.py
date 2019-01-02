from django.conf.urls import url
from django.contrib import admin
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render, reverse, HttpResponseRedirect
from django.utils.text import slugify
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory
from .models import Menu, MenuContent, MenuItem


class MenuContentAdmin(admin.ModelAdmin):
    exclude = ["menu"]

    def save_model(self, request, obj, form, change):
        if not change:
            # Creating grouper object for menu content
            obj.menu = Menu.objects.create(
                identifier=slugify(obj.title), site=get_current_site(request)
            )
        super().save_model(request, obj, form, change)

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            url(
                r"^(.+)/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="{}_{}_preview".format(*info),
            ),
            url(
                r"^(.+)/list/",
                self.admin_site.admin_view(self.edit_view),
                name="{}_{}_list".format(*info),
            ),
        ] + super().get_urls()

    def get_list_display(self, request):
        list_display = ["title", "get_menuitem_link"]
        return list_display

    def get_menuitem_link(self, obj):
        object_preview_url = reverse(
            "admin:{app}_menuitem_list".format(
                app=obj._meta.app_label, model=obj._meta.model_name
            ),
            args=[obj.pk],
        )

        return format_html(
            '<a href="{}" class="js-moderation-close-sideframe" target="_top">'
            '<span class="cms-icon cms-icon-eye"></span> Items'
            "</a>",
            object_preview_url,
        )

    get_menuitem_link.short_description = _("Menu Items")

    def preview_view(self, request, obj):
        menu = MenuItem.objects.filter(menu_content=obj)
        context = dict(object_id=request.GET.get("menu_id"), results=menu)
        return render(request, "admin/djangocms_navigation/menu_preview.html", context)

    def edit_view(self, request, obj):
        menu = MenuItem.objects.filter(menu_content=obj)
        context = dict(object_id=request.GET.get("menu_id"), results=menu)
        return render(request, "admin/djangocms_navigation/menu_preview.html", context)


class MenuItemAdmin(TreeAdmin):
    form = movenodeform_factory(MenuItem)
    change_list_template = "/admin/djangocms_navigation/menuitem/change_list.html"

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            url(
                r"^(?P<menucontent_id>\d+)/list/",
                self.admin_site.admin_view(self.changelist_view),
                name="{}_{}_list".format(*info),
            ),
            url(
                r"^(?P<menucontent_id>\d+)/add/",
                self.admin_site.admin_view(self.add_view),
                name="{}_{}_add".format(*info),
            ),
        ] + super().get_urls()

    def get_queryset(self, request):
        if hasattr(self, "menucontent"):
            return MenuItem.objects.filter(menu_content=self.menucontent)
        return self.model().get_tree()

    def add_view(self, request, menucontent_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if menucontent_id:
            self.menucontent = menucontent_id
        return super().add_view(request, form_url=form_url, extra_context=extra_context)

    def changelist_view(self, request, menucontent_id=None, extra_context=None):
        extra_context = extra_context or {}

        if menucontent_id:
            self.menucontent = menucontent_id
            extra_context["menucontent"] = self.menucontent
            extra_context["add_url"] = reverse(
                "admin:djangocms_navigation_menuitem_add",
                kwargs={"menucontent_id": self.menucontent},
            )

        return super().changelist_view(request, extra_context)

    def response_change(self, request, obj):
        url = reverse(
            "admin:djangocms_navigation_menuitem_list",
            kwargs={"menucontent_id": self.menucontent},
        )
        return HttpResponseRedirect(url)

    def response_add(self, request, obj, post_url_continue=None):
        url = reverse(
            "admin:djangocms_navigation_menuitem_list",
            kwargs={"menucontent_id": self.menucontent},
        )
        return HttpResponseRedirect(url)


admin.site.register(MenuItem, MenuItemAdmin)
admin.site.register(MenuContent, MenuContentAdmin)
