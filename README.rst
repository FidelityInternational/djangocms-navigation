====================
djangocms-navigation
====================

Installation
============

Requirements
============

django CMS Navigation requires that you have a django CMS 4.0 (or higher) project already running and set up.


To install
==========

Run::

    pip install djangocms-navigation

Add ``djangocms_navigation`` to your project's ``INSTALLED_APPS``.

Run::

    python manage.py migrate djangocms_navigation

to perform the application's database migrations.

App Integration
===============

To register model to use navigation app, app should provide class in cms_config.py which inherit `CMSAppConfig`
class. It should have `djangocms_navigation_enabled` flag True which register to use djangocms_navigation and
provide model mapping object, `navigation_models`.

Mapping object should provide Model class as key and list of model fields which will be used for autocomplete form fields. Example of
configuration defined below.


.. code-block:: python

    class CoreCMSAppConfig(CMSAppConfig):
        djangocms_navigation_enabled = True
        navigation_models = {
            Model: ["model_field", ],
        }

