import django

from packaging.version import Version


DJANGO_4_2 = Version(django.get_version()) >= Version('4.2')
