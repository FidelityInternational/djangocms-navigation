from django.contrib import admin
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from .models import Menu, MenuContent, MenuItem


class MenuContentAdmin(admin.ModelAdmin):
    exclude = ['modified_by', 'menu', ]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.menu = Menu.objects.create()
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


class MenuItemAdmin(TreeAdmin):
    form = movenodeform_factory(MenuItem)

    exclude = ['modified_by', ]

    def save_model(self, request, obj, form, change):
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


admin.site.register(MenuItem, MenuItemAdmin)
admin.site.register(MenuContent, MenuContentAdmin)
