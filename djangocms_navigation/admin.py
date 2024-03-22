import json

from django.apps import apps
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import quote
from django.contrib.admin.views.main import ChangeList
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import path, re_path, reverse, reverse_lazy
from django.utils.html import format_html, format_html_join
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.views.i18n import JavaScriptCatalog

from djangocms_versioning.admin import ExtendedVersionAdminMixin
from djangocms_versioning.constants import DRAFT
from djangocms_versioning.exceptions import ConditionFailed
from djangocms_versioning.helpers import get_admin_url, version_list_url
from djangocms_versioning.models import Version
from treebeard.admin import TreeAdmin

from .compat import TREEBEARD_4_5
from .conf import TREE_MAX_RESULT_PER_PAGE_COUNT
from .filters import LanguageFilter
from .forms import MenuContentForm, MenuItemForm
from .helpers import is_preview_url
from .models import Menu, MenuContent, MenuItem
from .utils import is_versioning_enabled, purge_menu_cache, reverse_admin_name
from .views import ContentObjectSelect2View, MessageStorageView


try:
    from djangocms_version_locking.helpers import (
        content_is_unlocked_for_user,
        version_is_locked,
    )

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


@admin.register(MenuContent)
class MenuContentAdmin(ExtendedVersionAdminMixin, admin.ModelAdmin):
    form = MenuContentForm
    menu_model = Menu
    menu_item_model = MenuItem
    list_display_links = None
    # Disable dropdown actions
    actions = None
    list_filter = (LanguageFilter, )

    class Media:
        js = ("admin/js/jquery.init.js", "djangocms_versioning/js/actions.js",)
        css = {"all": ("djangocms_versioning/css/actions.css", "djangocms_version_locking/css/version-locking.css",)}

    def _list_actions(self, request):
        """
        A closure that makes it possible to pass request object to
        list action button functions.
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
        actions = [
            self._get_preview_link,
            self._get_edit_link,
            self._get_manage_versions_link,
            self._get_references_link,
        ]

        if getattr(settings, "DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED", False):
            actions.append(self._get_main_navigation_link)

        return actions

    def get_list_display(self, request):
        menu_content_list_display = ["title"]
        versioning_enabled = is_versioning_enabled(self.model)

        if getattr(settings, "DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED", False):
            menu_content_list_display.extend(["get_main_navigation"])

        if versioning_enabled:
            menu_content_list_display.extend(
                ["get_author", "get_modified_date", "get_versioning_state"]
            )
            # Add version locking specific items
            if using_version_lock:
                menu_content_list_display.extend(["is_locked"])
                # Ensure actions are the last items
            menu_content_list_display.extend([self._list_actions(request)])
        else:
            menu_content_list_display.extend(["get_menuitem_link", "get_preview_link"])

        return menu_content_list_display

    @admin.display(
        description=_("Lock State")
    )
    def is_locked(self, obj):
        version = self.get_version(obj)
        if version.state == DRAFT and version_is_locked(version):
            return render_to_string("djangocms_version_locking/admin/locked_icon.html")
        return ""

    def _get_references_link(self, obj, request):
        menu_content_type = ContentType.objects.get(
            app_label=self.model._meta.app_label, model=Menu._meta.model_name,
        )

        url = reverse_lazy(
            "djangocms_references:references-index",
            kwargs={"content_type_id": menu_content_type.id, "object_id": obj.menu.id},
        )

        return render_to_string(
            "djangocms_references/references_icon.html",
            {"url": url}
        )

    @admin.display(
        description="Main Navigation",
        boolean=True,
    )
    def get_main_navigation(self, obj):
        """
        Return main_navigation field from Menu associated with MenuContent.
        :param: obj: MenuContent Instance
        :return: Boolean
        """
        return obj.menu.main_navigation

    def _get_main_navigation_link(self, obj, request, disabled=False):
        """
        Return an admin link to the confirmation page for setting main confirmations
        :param: obj: MenuContent Instance
        :param: request: Request
        :param: disabled: Boolean
        :return: Url
        """
        main_navigation_url = reverse(
            "admin:{app}_{model}_main_navigation".format(
                app=obj._meta.app_label, model=obj._meta.model_name,
            ),
            args=[obj.pk],
        )
        if obj.menu.main_navigation:
            disabled = True

        return render_to_string(
            "admin/djangocms_navigation/icons/main_navigation.html",
            {"url": main_navigation_url, "disabled": disabled}
        )

    def get_menuitem_link(self, obj):
        """
        Return an admin link to the menuitem
        :param obj: MenuItem Instance
        :return: Url
        """
        object_menuitem_url = reverse(
            "admin:{app}_{model}_list".format(
                app=obj._meta.app_label, model=self.menu_item_model._meta.model_name
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

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('menu').filter(
            menu__site=get_current_site(request))
        return queryset

    def save_model(self, request, obj, form, change):
        if not change:
            title = form.cleaned_data.get("title")
            # Creating grouper object for menu content
            obj.menu = self.menu_model.objects.create(
                identifier=slugify(title), site=get_current_site(request)
            )
            # Creating root menu item with title
            obj.root = self.menu_item_model.add_root(title=title)
        super().save_model(request, obj, form, change)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        meta = self.menu_item_model._meta
        return HttpResponseRedirect(
            reverse(
                "admin:{app}_{model}_list".format(
                    app=meta.app_label, model=meta.model_name
                ),
                args=[object_id],
            )
        )

    @admin.display(
        description=_("Menu Items")
    )
    def get_menuitem_link(self, obj):
        object_menuitem_url = reverse(
            "admin:{app}_{model}_list".format(
                app=obj._meta.app_label, model=self.menu_item_model._meta.model_name
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


@admin.register(MenuItem)
class MenuItemAdmin(TreeAdmin):
    form = MenuItemForm
    menu_content_model = MenuContent
    menu_model = Menu
    actions = None
    change_form_template = "admin/djangocms_navigation/menuitem/change_form.html"
    change_list_template = "admin/djangocms_navigation/menuitem/change_list.html"
    list_display = ["__str__", "get_object_url", "soft_root", 'hide_node']
    sortable_by = ["pk"]
    list_per_page = TREE_MAX_RESULT_PER_PAGE_COUNT

    class Media:
        css = {
            "all": (
                "djangocms_versioning/css/actions.css",
                "djangocms_navigation/css/navigation_admin_changelist.css",
            )
        }

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path(
                "",
                self.admin_site.admin_view(self.changelist_view),
                name="{}_{}_changelist".format(*info),
            ),
            path(
                "<int:menu_content_id>/",
                self.admin_site.admin_view(self.changelist_view),
                name="{}_{}_list".format(*info),
            ),
            path(
                "<int:menu_content_id>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="{}_{}_preview".format(*info),
            ),
            path(
                "<int:menu_content_id>/add/",
                self.admin_site.admin_view(self.add_view),
                name="{}_{}_add".format(*info),
            ),
            path(
                "<int:menu_content_id>/<int:object_id>/change/",
                self.admin_site.admin_view(self.change_view),
                name="{}_{}_change".format(*info),
            ),
            path(
                "<int:menu_content_id>/<int:object_id>/delete/",
                self.admin_site.admin_view(self.delete_view),
                name="{}_{}_delete".format(*info),
            ),
            path(
                "<int:menu_content_id>/move/",
                self.admin_site.admin_view(self.move_node),
                name="{}_{}_move_node".format(*info),
            ),
            path(
                "<int:menu_content_id>/jsi18n/",
                JavaScriptCatalog.as_view(packages=["treebeard"]),
            ),
            path(
                "select2/",
                self.admin_site.admin_view(ContentObjectSelect2View.as_view(
                    menu_content_model=self.menu_content_model,
                )),
                name="{}_select2_content_object".format(
                    self.model._meta.app_label
                )
            ),
            path(
                "<int:menu_content_id>/messages/",
                self.admin_site.admin_view(MessageStorageView.as_view()),
                name="{}_{}_message_storage".format(*info),
            ),
            re_path(
                r"^(?P<menu_content_id>\d+)/main_navigation/",
                self.admin_site.admin_view(self.set_main_navigation_view),
                name="{}_{}_main_navigation".format(self.model._meta.app_label,
                                                    self.menu_content_model._meta.model_name)
            ),
        ]

    def get_list_display(self, request):
        list_display = ["__str__", "get_object_url", "soft_root", 'hide_node']

        if is_preview_url(request):
            return list_display

        list_display.extend([self._list_actions(request)])
        return list_display

    def _list_actions(self, request):
        """
        A closure that makes it possible to pass request object to
        list action button functions.
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
        Collect rendered actions from implemented methods and return as list
        """
        return [
            self._get_edit_link,
            self._get_delete_link,
        ]

    def _get_edit_link(self, obj, request, disabled=False):
        app, model = self.model._meta.app_label, self.model._meta.model_name

        edit_url = reverse(
            "admin:{app}_{model}_change".format(app=app, model=model),
            args=[request.menu_content_id, obj.id]
        )

        return render_to_string(
            "djangocms_versioning/admin/icons/edit_icon.html",
            {"url": edit_url, "disabled": disabled, "object_id": obj.id}
        )

    def _get_delete_link(self, obj, request, disabled=False):
        app, model = self.model._meta.app_label, self.model._meta.model_name

        delete_url = reverse(
            "admin:{app}_{model}_delete".format(app=app, model=model),
            args=[request.menu_content_id, obj.id]
        )

        return render_to_string(
            "djangocms_versioning/admin/discard_icon.html",
            {"discard_url": delete_url, "disabled": disabled, "object_id": obj.id},
        )

    def get_queryset(self, request):
        if hasattr(request, "menu_content_id"):
            menu_content = get_object_or_404(
                self.menu_content_model._base_manager, id=request.menu_content_id
            )
            return self.model.get_tree(menu_content.root)
        return self.model().get_tree()

    def change_view(self, request, object_id, menu_content_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if menu_content_id:
            request.menu_content_id = menu_content_id

        if self._versioning_enabled:
            menu_content = get_object_or_404(
                self.menu_content_model._base_manager, id=menu_content_id
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
        extra_context["delete_url"] = reverse(
            "admin:{}_menuitem_delete".format(self.model._meta.app_label),
            kwargs={"menu_content_id": menu_content_id, "object_id": object_id},
        )
        return super().change_view(
            request, str(object_id), form_url="", extra_context=extra_context
        )

    def add_view(self, request, menu_content_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if menu_content_id:
            request.menu_content_id = menu_content_id
            if self._versioning_enabled:
                menu_content = get_object_or_404(
                    self.menu_content_model._base_manager, id=menu_content_id
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
                "admin:{}_menuitem_list".format(self.model._meta.app_label),
                kwargs={"menu_content_id": menu_content_id},
            )

        return super().add_view(request, form_url=form_url, extra_context=extra_context)

    def preview_view(self, request, menu_content_id, extra_context=None):
        """
        Renders a preview of the MenuContent and MenuItem objects in 'readonly' without actions.
        """
        self.change_list_template = self.get_changelist_template(request=request)
        extra_context = extra_context or {}

        request.menu_content_id = menu_content_id
        menu_content = get_object_or_404(
            self.menu_content_model._base_manager, id=menu_content_id
        )
        extra_context["title"] = f"Preview Menu: {str(menu_content)}"
        extra_context["menu_content"] = menu_content
        return super().changelist_view(request, extra_context)

    def get_changelist_template(self, request):
        """Returns the correct template for the request. The preview template is a stripped back readonly version of the
        standard change list template. This method should be overridden if a custom template should be used.
        :param: request: Request Object
        :return: a string to the correct template
        """
        if is_preview_url(request=request):
            return "admin/djangocms_navigation/menuitem/preview.html"
        elif TREEBEARD_4_5:
            return "admin/djangocms_navigation/menuitem/change_list.html"
        else:
            return "admin/djangocms_navigation/menuitem/tree_change_list.html"

    def changelist_view(self, request, menu_content_id=None, extra_context=None):
        self.change_list_template = self.get_changelist_template(request=request)
        extra_context = extra_context or {}

        if menu_content_id:
            request.menu_content_id = menu_content_id
            menu_content = get_object_or_404(
                self.menu_content_model._base_manager, id=menu_content_id
            )
            if self._versioning_enabled:
                version = Version.objects.get_for_content(menu_content)
                try:
                    version.check_modify(request.user)
                except ConditionFailed as error:
                    messages.error(request, str(error))
                    return HttpResponseRedirect(version_list_url(menu_content))
            extra_context["title"] = "Edit Menu: {}".format(menu_content.__str__())
            extra_context["menu_content"] = menu_content
            extra_context["versioning_enabled_for_nav"] = self._versioning_enabled

        return super().changelist_view(request, extra_context)

    def set_main_navigation_view(self, request, menu_content_id):
        """Sets the selected navigation as the main navigation, and unsets existing, 404 if invalid menu_content
        or setting not enabled
        :param: request: Request Object
        :param: menu_content_id: Integer PK for menucontent
        :return: redirect or 404
        """
        # Raise a 404 if the main_navigation functionality is disabled.
        if not getattr(settings, "DJANGOCMS_NAVIGATION_MAIN_NAVIGATION_ENABLED", False):
            raise Http404

        changelist_url = get_admin_url(self.menu_content_model, "changelist")
        menu_content = get_object_or_404(
            self.menu_content_model._base_manager, id=menu_content_id
        )
        menu = menu_content.menu
        menu_queryset = self.menu_model._base_manager.filter(
            site=menu.site,
            main_navigation=True,
            menucontent__language=menu_content.language,
        )
        if request.method == "POST":
            # If this is a POST method, then they have confirmed, change the main_navigation
            menu_queryset.update(main_navigation=False)
            menu.main_navigation = True
            menu.save()
            purge_menu_cache(site_id=menu.site_id)
            self.message_user(
                request, _(f"You have set the navigation {menu.identifier} as the main navigation.")
            )
            return redirect(changelist_url)

        # If this isn't a POST method, it is the first interaction, therefore render confirmation
        extra_context = {}
        if menu_queryset:
            extra_context = {"existing_menus": menu_queryset.values_list("identifier", flat=True).distinct()}
        context = dict(
            object_id=menu_content_id,
            set_main_url=reverse(
                "admin:{app}_{model}_main_navigation".format(
                    app=self.model._meta.app_label,
                    model=self.menu_content_model._meta.model_name,
                ),
                args=(menu_content_id,),
            ),
            back_url=changelist_url,
            extra_context=extra_context,
            menucontent=menu.identifier,
        )
        return render(
            request, "admin/djangocms_navigation/main_navigation_confirmation.html", context
        )

    def _get_to_be_deleted(self, nodes, node_list):
        """
        Recursively fetches the child nodes to be deleted in a structure that represents their nesting, so that the
        returned node list is structured so that it is rendered in the template with items nested correctly e.g:

        node_list = [
            child_node,
            [
                child_of_child,
                sibling_of_child_of_child,
            ],
            sibling_node,
        ]
        """
        child_node_list = []
        for node in nodes:
            child_node_list.append(f"Menu item: {node}")
            children = node.get_children()
            self._get_to_be_deleted(children, child_node_list)

        if child_node_list:
            node_list.append(child_node_list)

        return node_list

    def delete_view(self, request, object_id, menu_content_id=None, form_url="", extra_context=None):

        extra_context = extra_context or {}
        if menu_content_id:
            request.menu_content_id = menu_content_id
            list_url = reverse_admin_name(
                self.model,
                'list',
                kwargs={"menu_content_id": menu_content_id},
            )
            extra_context["list_url"] = list_url
            if self._versioning_enabled:
                menu_content = get_object_or_404(
                    self.menu_content_model._base_manager, id=menu_content_id
                )
                delete_perm = self.has_delete_permission(request, menu_content)
                if not delete_perm:
                    messages.error(request, LOCK_MESSAGE)
                    return HttpResponseRedirect(version_list_url(menu_content))

                menu_item = get_object_or_404(self.model, id=object_id)

                if menu_item.is_root():
                    messages.error(
                        request, _("This item is the root of a menu, therefore it cannot be deleted.")
                    )
                    return HttpResponseRedirect(list_url)
                version = Version.objects.get_for_content(menu_content)
                try:
                    version.check_modify(request.user)
                except ConditionFailed as error:
                    messages.error(request, str(error))
                    return HttpResponseRedirect(version_list_url(menu_content))

                extra_context["menu_name"] = menu_item
                to_be_deleted = [f"Menu item: {menu_item}"]
                extra_context["deleted_objects"] = self._get_to_be_deleted(menu_item.get_children(), to_be_deleted)

        return super().delete_view(request, str(object_id), extra_context)

    def response_delete(self, request, obj_display, obj_id):
        """
        Determine the HttpResponse for the delete_view stage.
        """
        opts = self.model._meta

        if IS_POPUP_VAR in request.POST:
            popup_response_data = json.dumps({
                'action': 'delete',
                'value': str(obj_id),
            })
            return TemplateResponse(request, self.popup_response_template or [
                'admin/%s/%s/popup_response.html' % (opts.app_label, opts.model_name),
                'admin/%s/popup_response.html' % opts.app_label,
                'admin/popup_response.html',
            ], {
                'popup_response_data': popup_response_data,
            })

        self.message_user(
            request,
            _('The %(name)s “%(obj)s” was deleted successfully.') % {
                'name': opts.verbose_name,
                'obj': obj_display,
            },
            messages.SUCCESS,
        )
        if self.has_change_permission(request, None):
            post_url = reverse_admin_name(
                self.model,
                'list',
                kwargs={"menu_content_id": request.menu_content_id},
            )
            preserved_filters = self.get_preserved_filters(request)
            post_url = add_preserved_filters(
                {'preserved_filters': preserved_filters, 'opts': opts}, post_url
            )
        else:
            post_url = reverse('admin:index', current_app=self.admin_site.name)
        return HttpResponseRedirect(post_url)

    def response_change(self, request, obj):
        msg = _('Menuitem %(menuitem)s was changed successfully.') % {'menuitem': obj.id}
        endpoint_name = "menuitem_list"
        endpoint_kwargs = {"menu_content_id": request.menu_content_id}
        if "_addanother" in request.POST:
            endpoint_name = "menuitem_add"
        elif "_continue" in request.POST:
            endpoint_name = "menuitem_change"
            msg = _('Menuitem %(menuitem)s was changed successfully. You can edit it below') % {'menuitem': obj.id}
            endpoint_kwargs.update({"object_id": obj.id})
        url = reverse(
            "admin:{}_{}".format(self.model._meta.app_label, endpoint_name),
            kwargs=endpoint_kwargs,
        )
        self.message_user(request, msg, messages.SUCCESS)

        return HttpResponseRedirect(url)

    def response_add(self, request, obj, post_url_continue=None):
        msg = _('Menuitem %(menuitem)s was changed successfully.') % {'menuitem': obj.id}
        endpoint_name = "menuitem_list"
        endpoint_kwargs = {"menu_content_id": request.menu_content_id}
        if "_addanother" in request.POST:
            endpoint_name = "menuitem_add"
        elif "_continue" in request.POST:
            endpoint_name = "menuitem_change"
            msg = _('Menuitem %(menuitem)s was changed successfully. You can edit it below') % {'menuitem': obj.id}
            endpoint_kwargs.update({"object_id": obj.id})
        url = reverse(
            "admin:{}_{}".format(self.model._meta.app_label, endpoint_name),
            kwargs=endpoint_kwargs,
        )
        self.message_user(request, msg, messages.SUCCESS)

        return HttpResponseRedirect(url)

    def move_node(self, request, menu_content_id):
        # Disallow moving of a node on anything other than a draft version
        if self._versioning_enabled:
            menu_content = get_object_or_404(
                self.menu_content_model._base_manager, id=menu_content_id
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

    def has_view_permission(self, request, obj=None):
        if not hasattr(request, "menu_content_id"):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not hasattr(request, "menu_content_id"):
            return False

        if obj and using_version_lock:
            unlocked = content_is_unlocked_for_user(obj, request.user)
            if not unlocked:
                return False

        return super().has_delete_permission(request, obj)

    def get_changelist(self, request, **kwargs):
        return MenuItemChangeList

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        menu_root = get_object_or_404(self.model, menucontent=request.menu_content_id)

        class Form(form_class):
            def __new__(cls, *args, **kwargs):
                kwargs["menu_root"] = menu_root
                return form_class(*args, **kwargs)

        return Form

    @admin.display(
        description=_("URL")
    )
    def get_object_url(self, obj):
        if obj.content:
            obj_url = obj.content.get_absolute_url()
            return format_html("<a href='{0}'>{0}</a>", obj_url)

    @property
    def _versioning_enabled(self):
        """Helper property to check if versioning is enabled for navigation"""

        return apps.get_app_config(
            self.model._meta.app_label
        ).cms_config.djangocms_versioning_enabled
