import unittest
from contextlib import contextmanager

from django import forms


class TestCase(unittest.TestCase):
    @contextmanager
    def assertNotRaises(self, exc_type):
        try:
            yield None
        except exc_type:
            raise self.failureException("{} raised".format(exc_type.__name__))


class WidgetTestForm(forms.Form):
    dummy_field = forms.CharField(label="dummy", required=False)
