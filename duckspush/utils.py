"""
This module defines various utilities
without necessarily any relations between them
"""

import errno
import exc
import time                                                

from duckspush import PROJECT_ROOT
from jinja2 import Environment, PackageLoader, TemplateNotFound
from os import path, makedirs, getcwd


def mkdir_p(p):
    """
    Equivalent of bash funnction mkdir -p
    Do not raise if directory already exists
    """
    try:
        makedirs(p)
    except OSError as e:
        if e.errno == errno.EEXIST and path.isdir(p):
            pass
        else: raise


def generate_template(template_name, dest, **args):
    if template_name == "datasources.py":
        output_file_path = path.join(dest, template_name)
    elif template_name == "widgets_settings.yaml":
        output_file_path = path.join(dest, template_name)
    else:
        raise TemplateNotFound

    with open(output_file_path, "w") as pusher_settings:
            env = Environment(loader=PackageLoader("duckspush",
                                                   "templates"))
            template = env.get_template(template_name)
            template_string = template.render(**args)
            pusher_settings.write(template_string.encode("utf-8"))


def timeit(method):

    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        time_msg = '%s took %s sec to run.' % (method.__name__, te-ts)
        return (time_msg, result)
    return timed
