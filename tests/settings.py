HELPER_SETTINGS = {
    "INSTALLED_APPS": [
        "djangocms_navigation",
        "djangocms_navigation.test_utils.app_1",
        "djangocms_navigation.test_utils.app_2",
        "djangocms_navigation.test_utils.polls",
        "djangocms_versioning",
    ],
    "DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION": False,
    "MIGRATION_MODULES": {
        "sites": None,
        "contenttypes": None,
        "auth": None,
        "cms": None,
        "menus": None,
        "polls": None,
        "text": None,
        "djangocms_navigation": None,
        "djangocms_versioning": None,
    },
}


def run():
    from djangocms_helper import runner

    runner.cms("djangocms_navigation", extra_args=[])


if __name__ == "__main__":
    run()
