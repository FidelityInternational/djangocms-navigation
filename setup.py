from setuptools import find_packages, setup

import djangocms_navigation


INSTALL_REQUIREMENTS = [
    "Django>=1.11,<3.0",
    "django-treebeard>=4.3",
    "django-cms",
]

TEST_REQUIREMENTS = [
    "djangocms_helper",
    "djangocms_versioning",
    "djangocms_version_locking",
    "djangocms-moderation",
    "factory_boy",
    "django_cms",
]


setup(
    name="djangocms-navigation",
    packages=find_packages(),
    include_package_data=True,
    version=djangocms_navigation.__version__,
    description=djangocms_navigation.__doc__,
    long_description=open("README.rst").read(),
    classifiers=[
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Software Development",
    ],
    install_requires=INSTALL_REQUIREMENTS,
    author="Fidelity International",
    url="https://github.com/fidelityInternational/djangocms-navigation",
    license="BSD",
    test_suite="tests.settings.run",
    tests_require=TEST_REQUIREMENTS,
    dependency_links=[
        "http://github.com/divio/django-cms/tarball/release/4.0.x#egg=django-cms-4.0.0",
        "http://github.com/divio/djangocms-versioning/tarball/master#egg=djangocms-versioning-0.0.23",
        "http://github.com/divio/djangocms-moderation/tarball/release/1.0.x#egg=djangocms-moderation-1.0.x",
        "http://github.com/FidelityInternational/djangocms-version-locking/tarball/master#egg=djangocms-version-locking-0.0.13",  # noqa
        "-e git+https://github.com/divio/django-cms.git@release/4.0.x#egg=django-cms",
    ]
)
