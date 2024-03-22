HELPER_SETTINGS = {
    "SECRET_KEY": "Navigationtestsuitekey",
    "INSTALLED_APPS": [
        "djangocms_alias",
        "djangocms_navigation",
        "djangocms_navigation.test_utils.app_1",
        "djangocms_navigation.test_utils.app_2",
        "djangocms_navigation.test_utils.polls",
        "djangocms_versioning",
        "djangocms_version_locking",
        "djangocms_moderation",
        "djangocms_references",
    ],
    "CMS_CONFIRM_VERSION4": True,
    "DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION": False,
    "MIGRATION_MODULES": {
        "sites": None,
        "contenttypes": None,
        "auth": None,
        "cms": None,
        "menus": None,
        "polls": None,
        "text": None,
        "djangocms_alias": None,
        "djangocms_navigation": None,
        "djangocms_versioning": None,
        'djangocms_version_locking': None,
        'djangocms_moderation': None,
        "djangocms_references": None,
    },
    "LANGUAGES": (
        ("en", "English"),
        ("de", "German"),
        ("fr", "French"),
        ("it", "Italiano"),
    ),
    "DEFAULT_AUTO_FIELD": "django.db.models.AutoField",
    "ROOT_URLCONF": "tests.urls",
}


def run():
    from app_helper import runner
    runner.cms("djangocms_navigation", extra_args=[])
    from cms.test_utils.testcases import CMSTestCase
    from cms.utils.compat import DJANGO_4_1
    if DJANGO_4_1:
        CMSTestCase.assertQuerySetEqual = CMSTestCase.assertQuerysetEqual


if __name__ == "__main__":
    run()
