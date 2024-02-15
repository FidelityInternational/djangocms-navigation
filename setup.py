from setuptools import find_packages, setup

import djangocms_navigation


INSTALL_REQUIREMENTS = [
    "Django>=1.11,<3.3",
    "django-treebeard>=4.3,<4.6.0",
    "django-cms",
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
)
