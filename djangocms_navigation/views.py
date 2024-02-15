from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.views.generic import View

from cms.models import Page
from cms.utils import get_current_site, get_language_from_request

from djangocms_navigation.utils import is_model_supported, supported_models


class ContentObjectSelect2View(View):
    menu_content_model = None

    def get(self, request, *args, **kwargs):

        content_type_id = self.request.GET.get("content_type_id", None)
        # Return http bad request if there is no content_type_id provided in request
        if not content_type_id:
            return HttpResponseBadRequest()

        # return http bad request if content_type not exist in db
        try:
            content_object = ContentType.objects.get_for_id(content_type_id)
        except ContentType.DoesNotExist:
            return HttpResponseBadRequest()

        # return http bad request if content type is not registered to use navigation app
        model = content_object.model_class()
        if not is_model_supported(self.menu_content_model, model):
            return HttpResponseBadRequest()

        queryset_data = self.get_data()

        # Removing unpublished pages from queryset
        if model == Page:
            queryset_data = [
                page for page in queryset_data
                if getattr(page.get_title_obj().versions.first(), "state", None)
                != 'unpublished'
            ]

        data = {
            "results": [{"text": str(obj), "id": obj.pk} for obj in queryset_data]
        }
        return JsonResponse(data)

    def get_data(self):
        content_type_id = self.request.GET.get("content_type_id", None)
        query = self.request.GET.get("query", None)
        site = self.request.GET.get("site", get_current_site())
        content_object = ContentType.objects.get_for_id(content_type_id)
        model = content_object.model_class()
        language = get_language_from_request(self.request)

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

        if hasattr(queryset, "on_site"):
            queryset = queryset.on_site(site)
        elif hasattr(model, "site"):
            queryset = queryset.filter(site=site)

        if pk:
            queryset = queryset.filter(pk=pk)

        # TODO: filter by publish state?
        if model == Page:
            # limit the queryset to objects for the correct site and language
            queryset = queryset.filter(pagecontent_set__language=language, node__site=site).distinct()

        if not query:
            return queryset

        # Filter against field(s) defined on the CMSAppConfig.navigation_models attribute
        search_fields = supported_models(self.menu_content_model).get(model)
        query_dict = {field: query for field in search_fields}
        # build the filter query using the OR operator to search against all defined fields
        query = Q(**query_dict, _connector=Q.OR)
        # the filter could be across tables so distinct should be used
        return queryset.filter(query).distinct()


class MessageStorageView(View):

    def get(self, request, *args, **kwargs):
        storage = get_messages(request)
        data = {'messages': [{'message': m.message, 'level': m.level_tag} for m in storage]}

        return JsonResponse(data)
