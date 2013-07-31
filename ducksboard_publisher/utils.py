"""
This module defines various utilities
without necessarily any relations between them
"""

import errno
import exc

from ducksboard_publisher import PROJECT_ROOT
from jinja2 import Environment, PackageLoader, TemplateNotFound
from os import path, makedirs

def mkdir_p(path):
    """
    Equivalent of bash funnction mkdir -p
    Do not raise if directory already exists
    """
    try:
        makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise


def generate_template(template_name, **args):
    project_path = path.join(PROJECT_ROOT, "collect_project")
    if template_name == "collectors.py":
       output_file_path = path.join(project_path, template_name)
    elif template_name == "widget_settings.yaml":
        output_file_path = path.join(project_path, template_name)
    elif template_name == "publisher_settings.yaml":
       output_file_path = path.join(PROJECT_ROOT, template_name)
    else:
        raise TemplateNotFound

    env = Environment(loader=PackageLoader("ducksboard_publisher",
                                           "templates"))

    with open(output_file_path, "w") as publisher_settings:
            env = Environment(loader=PackageLoader("ducksboard_publisher",
                                                   "templates"))
            template = env.get_template(template_name)
            template_string = template.render(**args)
            publisher_settings.write(template_string.encode("utf-8"))
