from setuptools import find_packages, setup

import djangocms_navigation


INSTALL_REQUIREMENTS = [
    'Django>=1.11,<2.0',
    'django-cms>=3.5.0',
    'django-treebeard>=4.3'
    ]


setup(
    name='djangocms-navigation',
    packages=find_packages(),
    include_package_data=True,
    version=djangocms_navigation.__version__,
    description=djangocms_navigation.__doc__,
    long_description=open('README.rst').read(),
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
    install_requires=INSTALL_REQUIREMENTS,
    author='Fidelity International',
    url='https://github.com/fidelityInternational/djangocms-navigation',
    license='BSD',
    test_suite='tests.settings.run',
)

[flake8]
max-line-length = 120
exclude =
    .git,
    __pycache__,
    **/migrations/,
    build/,
    .tox/,

[isort]
line_length = 79
multi_line_output = 3
lines_after_imports = 2
combine_as_imports = true
include_trailing_comma = true
balanced_wrapping = true
skip = manage.py, migrations, .tox
known_standard_library = mock
known_django = django
known_cms = cms, menus
known_first_party = djangocms_navigation
sections = FUTURE, STDLIB, DJANGO, CMS, THIRDPARTY, FIRSTPARTY, LIB, LOCALFOLDER

[coverage:run]
branch = True
source = djangocms_navigation
omit =
    *apps.py,
    *constants.py,
    *migrations/*,
    *test_utils/*,
    *tests/*,

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
