import sys

from django.conf import settings


TREE_MAX_RESULT_PER_PAGE_COUNT = getattr(
    settings, "DJANGOCMS_NAVIGATION_TREE_MAX_RESULT_PER_PAGE_COUNT", sys.maxsize
)
