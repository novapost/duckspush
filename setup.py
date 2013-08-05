# coding=utf-8
"""Python packaging."""
import os
from setuptools import setup


def read_relative_file(filename):
    """Returns contents of the given file, which path is supposed relative
    to this module."""
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return f.read()


NAME = 'duckspush'
README = read_relative_file('README.md')
VERSION = read_relative_file('VERSION').strip()
PACKAGES = ['duckspush']
REQUIRES = ['gevent', 'pyaml', 'jinja2', 'respire']


setup(name=NAME,
      version=VERSION,
      description='A pusher for ducksboard widgets.',
      long_description=README,
      classifiers=['Development Status :: 1 - Planning',
                   'License :: OSI Approved :: BSD License',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 2.6',
                   ],
      keywords='ducksboard, ducksboard-pusher',
      author='Jonathan Dorival',
      author_email='jonathan.dorival@novapost.fr',
      url='https://github.com/jojax/%s' % NAME,
      license='BSD',
      packages=PACKAGES,
      include_package_data=True,
      zip_safe=False,
      install_requires=REQUIRES,
      entry_points={
        'console_scripts': [
            'start_push_project = duckspush.pusher:start_push_project',
            'remove_push_project = duckspush.pusher:remove_push_project',
            'run_pusher = duckspush.pusher:run_pusher',
            ]
        },
      )
