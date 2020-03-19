from django.apps import apps
from django.core import urlresolvers
from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin.utils import quote
from django.contrib.admin.views.main import ChangeList
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.views.i18n import JavaScriptCatalog

from treebeard.admin import TreeAdmin

from djangocms_pageadmin.helpers import proxy_model
from djangocms_versioning.constants import DRAFT, PUBLISHED
from djangocms_version_locking.helpers import version_is_locked

from .constants import SELECT2_CONTENT_OBJECT_URL_NAME
from .forms import MenuContentForm, MenuItemForm
from .models import Menu, MenuContent, MenuItem
from .utils import purge_menu_cache
from .views import ContentObjectSelect2View, MenuContentPreviewView


# TODO: Tests to be added
try:
    from djangocms_versioning.exceptions import ConditionFailed
    from djangocms_versioning.helpers import version_list_url
    from djangocms_versioning.models import Version
except ImportError:
    pass


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
    """
    The portions of this class that deal with rendering additional icons pertinent to versioning are taken from
    djangocms pagedmin which can be found here:
    https://github.com/FidelityInternational/djangocms-pageadmin/blob/master/djangocms_pageadmin/admin.py
    """
    form = MenuContentForm
    list_display = [
        "title", "get_versioning_state", "get_author", "get_modified_date", "get_state_display", "is_locked"
    ]
    list_display_links = None

    def get_version(self, obj):
        """
        Taken from djangocms pageadmin
        """
        return obj.versions.all()[0]

    def get_versioning_state(self, obj):
        return self.get_version(obj).get_state_display()

    get_versioning_state.short_description = _("Lock Status")

    def is_locked(self, obj):
        version = self.get_version(obj)
        if version.state == DRAFT and version_is_locked(version):
            return render_to_string("djangocms_version_locking/admin/locked_icon.html")
        return ""

    is_locked.short_description = _("Lock Status")

    def get_state_display(self, obj):
        return self.get_version(obj).get_state_display()

    get_state_display.short_description = _("State")

    def get_author(self, obj):
        return self.get_version(obj).created_by

    get_author.short_description = _("Author")

    def get_modified_date(self, obj):
        return self.get_version(obj).modified

    get_modified_date.short_description = _("Modified")

    def _list_actions(self, request):
        """A closure that makes it possible to pass request object to
        list action button functions.

        Taken from djangocms pageadmin
        """

        def list_actions(obj):
            """Display links to state change endpoints
            """
            return format_html_join(
                "",
                "{}",
                ((action(obj, request),) for action in self.get_list_actions()),
            )

        list_actions.short_description = _("actions")
        return list_actions

    def get_list_actions(self):
        """
        Taken from djangocms pageadmin
        """
        return [
            self._get_preview_link,
            self._get_edit_link,
        ]

    def get_list_display(self, request):
        """
        Taken from djangocms pageadmin
        """
        return self.list_display + [self._list_actions(request)]

    def _get_preview_link(self, obj, request, disabled=False):
        """
        Taken from djangocms pageadmin
        """
        return render_to_string(
            "djangocms_pageadmin/admin/icons/preview.html",
            {"url": obj.get_preview_url(), "disabled": disabled},
        )

    def _get_edit_link(self, obj, request, disabled=False):
        """
        Taken from djangocms pageadmin
        """
        version = proxy_model(self.get_version(obj))

        if version.state not in (DRAFT, PUBLISHED):
            # Don't display the link if it can't be edited
            return ""

        if not version.check_edit_redirect.as_bool(request.user):
            disabled = True

        url = reverse(
            "admin:{app}_{model}_list".format(
                app=obj._meta.app_label, model=MenuItem._meta.model_name
            ),
            args=[obj.pk],
        )
        return render_to_string(
            "djangocms_pageadmin/admin/icons/edit.html",
            {"url": url, "disabled": disabled, "post": False},
        )

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
        extra_context = extra_context or {}
        form_url = reverse(
            "admin:{app}_{model}_list".format(
                app=meta.app_label, model=meta.model_name
            ), args=[object_id],
        )
        return super(MenuContentAdmin, self).change_view(
            request, object_id, form_url=form_url, extra_context=extra_context
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

    class Media:
        css = {"all": ("djangocms_pageadmin/css/actions.css", "djangocms_version_locking/css/version-locking.css",)}




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
            extra_context["title"] = "Edit Menu: {}".format(menu_content.__str__())
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
