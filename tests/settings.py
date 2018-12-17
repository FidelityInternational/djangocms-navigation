HELPER_SETTINGS = {
    "INSTALLED_APPS": [
        "djangocms_navigation",
        "djangocms_navigation.test_utils.app_1",
        "djangocms_navigation.test_utils.app_2",
    ]
}


def run():
    from djangocms_helper import runner

    runner.cms("djangocms_navigation", extra_args=[])


if __name__ == "__main__":
    run()
