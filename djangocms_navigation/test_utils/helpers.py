from bs4 import BeautifulSoup


def get_nav_from_response(response):
    """
    Takes a response object and returns soup object of the navigation menu

    :param response: A TemplateResponse object
    """
    return BeautifulSoup(str(response.content), features="lxml").find("ul", class_="nav")


def make_main_navigation(menucontent):
    """
    Helper that takes a menucontent object, gets the related Menu grouper object, and marks it as the main
    navigation menu. This is a change that would be made in the admin by a user, but we make the change directly to
    the object for the purpose of testing.

    :param menucontent: A MenuContent object
    """
    menu = menucontent.menu
    menu.main_navigation = True
    menu.save()
