from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views.generic import ListView

from cms.models import Page

from djangocms_navigation.utils import is_model_supported, supported_models


class ContentObjectSelect2View(ListView):
    def get(self, request, *args, **kwargs):

        self.site = get_current_site(request)
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        data = {
            "results": [
                {"text": str(obj), "id": obj.pk} for obj in context["object_list"]
            ],
            "more": context["page_obj"].has_next(),
        }
        return JsonResponse(data)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        content_type_id = self.request.GET.get("content_type_id", None)

        query = self.request.GET.get("search_text", None)
        site = self.request.GET.get("site")
        try:
            content_object = ContentType.objects.get_for_id(content_type_id)
        except ContentType.DoesNotExist:
            raise ValueError(
                "Content type with id {} does not exists.".format(content_type_id)
            )

        model = content_object.model_class()
        search_fields = supported_models().get(model)
        if not is_model_supported(model):
            raise ValueError(
                "{} is not available to use, check content_id param".format(model)
            )

        try:
            # If versioning is enabled then get versioning queryset for model
            app_config = apps.get_app_config("djangocms_versioning")
            versionable_item = app_config.cms_extension.versionables_by_grouper[model]
            queryset = versionable_item.grouper_choices_queryset()
        except (LookupError, KeyError):
            queryset = model.objects.all()

        try:
            pk = int(self.request.GET.get("pk"))
        except (TypeError, ValueError):
            pk = None

        if site:
            if hasattr(model.objects, "on_site"):
                queryset = queryset.on_site(site)
            elif hasattr(model, "site"):
                queryset = queryset.filter(site=site)

        if pk:
            queryset = queryset.filter(pk=pk)

        if query:
            # For Page model loop through all title objects to exclude the
            # object which doesnt match query
            if model == Page:
                for item in queryset:
                    if item.get_page_title().lower().find(query.lower()) == -1:
                        queryset = queryset.exclude(pk=item.pk)
            else:
                # Non page model should work using filter against field in queryset
                options = {}
                for field in search_fields:
                    options[field] = query

                queryset = queryset.filter(**options)

        return queryset

    def get_paginate_by(self, queryset):
        return self.request.GET.get("limit", 30)
