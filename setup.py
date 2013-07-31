# coding=utf-8
"""Python packaging."""
import os
from setuptools import setup


def read_relative_file(filename):
    """Returns contents of the given file, which path is supposed relative
    to this module."""
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return f.read()


NAME = 'django-js-error-hook'
README = read_relative_file('README.md')
VERSION = read_relative_file('VERSION').strip()
PACKAGES = ['ducksboard_publisher']
REQUIRES = ['gevent', 'pyaml', 'jinja2', 'respire']


setup(name=NAME,
      version=VERSION,
      description='A publisher for ducksboard widgets.',
      long_description=README,
      classifiers=['Development Status :: 1 - Planning',
                   'License :: OSI Approved :: BSD License',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 2.6',
                   ],
      keywords='ducksboard, ducksboard-publisher',
      author='Jonathan Dorival',
      author_email='jonathan.dorival@novapost.fr',
      url='https://github.com/jojax/%s' % NAME,
      license='BSD',
      packages=PACKAGES,
      include_package_data=True,
      zip_safe=False,
      install_requires=REQUIRES,
      )
