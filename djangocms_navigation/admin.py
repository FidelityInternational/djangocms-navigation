from django.contrib import admin
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from .models import Menu, MenuItem


class MenuAdmin(admin.ModelAdmin):
    exclude = ['created_by', ]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            # Only set created_by during the first save.
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class NodeAdmin(TreeAdmin):
    form = movenodeform_factory(MenuItem)

    exclude = ['created_by', ]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            # Only set created_by during the first save.
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


admin.site.register(MenuItem, NodeAdmin)
admin.site.register(Menu, MenuAdmin)
