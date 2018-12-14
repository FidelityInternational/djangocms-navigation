from django.contrib import admin
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from .models import Menu, MenuContent, MenuItem


class MenuContentAdmin(admin.ModelAdmin):
    exclude = ['menu', ]

    def save_model(self, request, obj, form, change):
        if not change:
            # Creating grouper object for menu content
            obj.menu = Menu.objects.create()
        super().save_model(request, obj, form, change)


class MenuItemAdmin(TreeAdmin):
    form = movenodeform_factory(MenuItem)

admin.site.register(MenuItem, MenuItemAdmin)
admin.site.register(MenuContent, MenuContentAdmin)
