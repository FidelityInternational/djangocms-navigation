=========
Changelog
=========

Unreleased
==========
* Python 3.10 support added
* Python 3.7 support removed
* Django 4.2 support added
* Django 2.2 support removed

1.8.3 (2024-03-06)
==================
* feat: Removed unpublished pages from menu item admin select view for page drop down

1.8.2 (2022-10-25)
==================
* fix: delete confirmation screen displays all nodes to be deleted, with each node nested
correctly to match the standard django delete confirmation view

1.8.1 (2022-10-21)
==================
* fix: safely checks for a MenuContent object in the context provided to the results tree templatetag, rather than
assume there is always one, to guard against 500 errors

1.8.0 (2022-10-13)
==================
* feat: store a list of expanded nodes in a page session object so after editing a menu the
previous state is displayed

1.7.0 (2022-09-21)
==================
* feat: display confirmation dialog when moving a menu item node

1.6.2 (2022-09-15)
==================
* fix: increase minimist version to fix vulnerability

1.6.1 (2022-09-15)
==================
* fix: filter main navigation menu queryset by the current site

1.6.0 (2022-09-13)
==================
* feat: When adding a MenuItem the Page objects are filtered by PageUrl slug and path

1.5.1 (2022-08-26)
==================
* fix: Remove duplicate objects when adding MenuItem nodes
* fix: When adding a MenuItem the Page objects are filtered for the current site and language

1.5.0 (2022-08-22)
==================
* feat: Improved MenuItemAdmin preview_view to allow the user to view the full navigation tree
and use expand/collapse commands for all nodes in the tree.
* feat: Button to switch to edit mode when viewing a navigation menu in preview.
* fix: Added CMS_CONFIRM_VERSION4 in test_settings to show intent of using v4

1.4.0 (2022-08-12)
==================
* feat: Main navigation, to allow the use of more than one navigation for a given site/language
while preserving existing functionality.

1.3.0 (2022-07-07)
==================
* feat: Navigation nodes with a page attached use the preview url in the edit or preview mode.
* feat: Replaced CircleCi with GitHub Actions for the test runner

1.2.0 (2022-05-25)
==================
* feat: MenuContent compare view renders menu changes

1.1.0 (2022-04-06)
==================
* feat: MenuContent Changelist now uses ExtendedVersionAdminMixin

1.0.7 (2022-04-01)
==================
* feat: MenuItem tree removed pagination with the option to configure the paging amount

1.0.6 (2022-03-29)
==================
* fix: Moved admin list actions to appropriate menu

1.0.5 (2022-03-24)
==================
* feat: Admin list action for references

1.0.4 (2022-03-18)
==================
* feat: Expand/collapse ALL nodes for navigation tree in admin changelist view.

1.0.3 (2022-03-15)
==================
* feat: Expand/collapse enabled for navigation tree in admin changelist view.
* feat: Added delete confirmation template to overwrite delete view breadcrumbs
* fix: Extended app Node deletion 404 bugfix

1.0.2 (2022-03-03)
==================
* feat: MenuContent and MenuItem links open in sideframe (refactored icons)

1.0.1 (2022-03-01)
===================
* feat: MenuContent dropdown actions removed
* feat: MenuItem edit button added as list action button
* feat: Hide the MenuItem boolean false icon for `Hide in Menu` and `Soft Root` fields.
* feat: MenuItem changelist admin, remove the option to sort by `Hide In Menu` and `Soft Root`.

1.0.0 (2022-02-18)
===================
* MenuItem delete moved from dropdown action to individual delete action button
* Python 3.8, 3.9 support added
* Django 3.0, 3.1 and 3.2 support added
* Python 3.5 and 3.6 support removed
* Django 1.11 support removed
