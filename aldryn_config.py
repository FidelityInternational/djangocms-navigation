from aldryn_client import forms


class Form(forms.BaseForm):
    def to_settings(self, data, settings):
        settings['DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION'] = False
        return settings
