from django.contrib import admin
from django.contrib.sites.shortcuts import get_current_site
from django.utils.text import slugify

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from .models import Menu, MenuContent, MenuItem


class MenuContentAdmin(admin.ModelAdmin):
    exclude = ['menu', ]

    def save_model(self, request, obj, form, change):
        if not change:
            # Creating grouper object for menu content
            obj.menu = Menu.objects.create(
                identifier=slugify(
                    obj.title
                ),
                site=get_current_site(request),
            )
        super().save_model(request, obj, form, change)


class MenuItemAdmin(TreeAdmin):
    form = movenodeform_factory(MenuItem)


admin.site.register(MenuItem, MenuItemAdmin)
admin.site.register(MenuContent, MenuContentAdmin)
