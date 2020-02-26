from django.apps import apps
from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin.utils import quote
from django.contrib.admin.views.main import ChangeList
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.views.i18n import JavaScriptCatalog

from treebeard.admin import TreeAdmin

from .constants import SELECT2_CONTENT_OBJECT_URL_NAME
from .forms import MenuContentForm, MenuItemForm
from .models import Menu, MenuContent, MenuItem
from .utils import purge_menu_cache, reverse_admin_name
from .views import ContentObjectSelect2View, MenuContentPreviewView


# TODO: Tests to be added
try:
    from djangocms_versioning.exceptions import ConditionFailed
    from djangocms_versioning.helpers import version_list_url
    from djangocms_versioning.models import Version
except ImportError:
    pass

try:
    from djangocms_version_locking.helpers import content_is_unlocked_for_user
    using_version_lock = True
    LOCK_MESSAGE = _(
        "The item is currently locked or you don't "
        "have permission to change it"
    )
except ImportError:
    using_version_lock = False
    LOCK_MESSAGE = _("You don't have permission to change this item")


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
    list_display = ["title", "get_menuitem_link", "get_preview_link"]
    list_display_links = None

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('menu').filter(
            menu__site=get_current_site(request))
        return queryset

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
        object_menuitem_url = reverse(
            "admin:{app}_{model}_list".format(
                app=obj._meta.app_label, model=MenuItem._meta.model_name
            ),
            args=[obj.pk],
        )

        return format_html(
            '<a href="{}" class="js-moderation-close-sideframe" target="_top">'
            '<span class="cms-icon cms-icon-eye"></span> {}'
            "</a>",
            object_menuitem_url,
            _("Items"),
        )

    get_menuitem_link.short_description = _("Menu Items")

    def get_preview_link(self, obj):
        return format_html(
            '<a href="{}" class="js-moderation-close-sideframe" target="_top">'
            '<span class="cms-icon cms-icon-eye"></span> {}'
            "</a>",
            obj.get_preview_url(),
            _("Preview"),
        )

    get_menuitem_link.short_description = _("Menu Preview")


class MenuItemAdmin(TreeAdmin):
    form = MenuItemForm
    change_list_template = "admin/djangocms_navigation/menuitem/change_list.html"
    list_display = ["__str__", "get_object_url"]

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
                name="{}_{}_move_node".format(*info),
            ),
            url(
                r"^(?P<menu_content_id>\d+)/jsi18n/$",
                JavaScriptCatalog.as_view(packages=["treebeard"]),
            ),
            url(
                r"^select2/$",
                self.admin_site.admin_view(ContentObjectSelect2View.as_view()),
                name=SELECT2_CONTENT_OBJECT_URL_NAME,
            ),
            url(
                r"^(?P<menu_content_id>\d+)/preview/$",
                self.admin_site.admin_view(MenuContentPreviewView.as_view()),
                name="{}_{}_preview".format(*info),
            ),
        ]

    def get_queryset(self, request):
        if hasattr(request, "menu_content_id"):
            menu_content = get_object_or_404(
                MenuContent._base_manager, id=request.menu_content_id
            )
            return MenuItem.get_tree(menu_content.root)
        return self.model().get_tree()

    def change_view(
        self, request, object_id, menu_content_id=None, form_url="", extra_context=None
    ):
        extra_context = extra_context or {}
        if menu_content_id:
            request.menu_content_id = menu_content_id

        if self._versioning_enabled:
            menu_content = get_object_or_404(
                MenuContent._base_manager, id=menu_content_id
            )

            change_perm = self.has_change_permission(request, menu_content)
            if not change_perm:
                messages.error(request, LOCK_MESSAGE)
                return HttpResponseRedirect(version_list_url(menu_content))

            version = Version.objects.get_for_content(menu_content)
            try:
                version.check_modify(request.user)
            except ConditionFailed as error:
                messages.error(request, str(error))
                return HttpResponseRedirect(version_list_url(menu_content))
            # purge menu cache
            purge_menu_cache(site_id=menu_content.menu.site_id)
        extra_context["list_url"] = reverse_admin_name(
            self.model,
            'list',
            kwargs={"menu_content_id": menu_content_id},
        )

        return super().change_view(
            request, object_id, form_url="", extra_context=extra_context
        )

    def add_view(self, request, menu_content_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if menu_content_id:
            request.menu_content_id = menu_content_id
            if self._versioning_enabled:
                menu_content = get_object_or_404(
                    MenuContent._base_manager, id=menu_content_id
                )
                version = Version.objects.get_for_content(menu_content)
                try:
                    version.check_modify(request.user)
                except ConditionFailed as error:
                    messages.error(request, str(error))
                    return HttpResponseRedirect(version_list_url(menu_content))
                # purge menu cache
                purge_menu_cache(site_id=menu_content.menu.site_id)
            extra_context["list_url"] = reverse(
                "admin:djangocms_navigation_menuitem_list",
                kwargs={"menu_content_id": menu_content_id},
            )

        return super().add_view(request, form_url=form_url, extra_context=extra_context)

    def changelist_view(self, request, menu_content_id=None, extra_context=None):
        extra_context = extra_context or {}

        if menu_content_id:
            request.menu_content_id = menu_content_id
            menu_content = get_object_or_404(
                MenuContent._base_manager, id=menu_content_id
            )
            if self._versioning_enabled:
                version = Version.objects.get_for_content(menu_content)
                try:
                    version.check_modify(request.user)
                except ConditionFailed as error:
                    messages.error(request, str(error))
                    return HttpResponseRedirect(version_list_url(menu_content))
            extra_context["menu_content"] = menu_content
            extra_context["versioning_enabled_for_nav"] = self._versioning_enabled

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
        # Disallow moving of a node on anything other than a draft version
        if self._versioning_enabled:
            menu_content = get_object_or_404(
                MenuContent._base_manager, id=menu_content_id
            )
            request.menu_content_id = menu_content_id
            change_perm = self.has_change_permission(request, menu_content)
            if not change_perm:
                messages.error(request, LOCK_MESSAGE)
                return HttpResponseBadRequest(LOCK_MESSAGE)

            version = Version.objects.get_for_content(menu_content)
            try:
                version.check_modify(request.user)
            except ConditionFailed as error:
                messages.error(request, str(error))
                return HttpResponseBadRequest(str(error))

        # Disallow moving of a node outside of the menu it is part of
        if request.POST.get("parent_id") == "0":
            message = _("Cannot move a node outside of the root menu node")
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

        if obj and using_version_lock:
            unlocked = content_is_unlocked_for_user(obj, request.user)
            if not unlocked:
                return False

        return super().has_change_permission(request, obj)

    def get_changelist(self, request, **kwargs):
        return MenuItemChangeList

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        menu_root = get_object_or_404(MenuItem, menucontent=request.menu_content_id)

        class Form(form_class):
            def __new__(cls, *args, **kwargs):
                kwargs["menu_root"] = menu_root
                return form_class(*args, **kwargs)

        return Form

    def get_object_url(self, obj):
        if obj.content:
            obj_url = obj.content.get_absolute_url()
            return format_html("<a href='{0}'>{0}</a>", obj_url)

    get_object_url.short_description = _("URL")

    @property
    def _versioning_enabled(self):
        """Helper property to check if versioning is enabled for navigation"""
        return apps.get_app_config(
            "djangocms_navigation"
        ).cms_config.djangocms_versioning_enabled


admin.site.register(MenuItem, MenuItemAdmin)
admin.site.register(MenuContent, MenuContentAdmin)
