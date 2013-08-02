# -*- coding: iso-8859-1 -*-

import gevent.monkey
gevent.monkey.patch_all()
import gevent
import api
import exc
import os
import time
import utils
import shutil
import signal
import sys
import yaml

from duckspush import PROJECT_ROOT
from os import path
from optparse import OptionParser
from requests import HTTPError


## TODO break into multiple funcs
class Widget(yaml.YAMLObject):
    yaml_tag = u'!Widget'

    def __init__(self, wid, title, kind, endpoints):
        self.wid = wid
        self.title = title
        self.kind = kind
        self.endpoints = endpoints

    def collect_endpoints_data(self):
        data = dict()
        for e in self.endpoints:
            data[e.endpoint_id] = e.collector.collect()
        return data

    def __str__(self):
        return str(self.__dict__)


class WidgetEndpoint(yaml.YAMLObject):

    yaml_tag = u'!WidgetEndpoint'

    def __init__(self, eid, subtitle, collector):
        self.endpoint_id = eid
        self.subtitle = subtitle
        self.collector = collector

    def __str__(self):
        return str(self.__dict__)


class DataCollector(yaml.YAMLObject):
    yaml_tag = u'!DataCollector'

    def __init__(self, collector_func_name, **kwargs):
        self.collector_func_name = collector_func_name
        self.func_kwargs = kwargs

    def collect(self):
        from collect_project import collectors
        collect_func = getattr(collectors, self.collector_func_name)
        return collect_func(**self.func_kwargs)

    def __str__(self):
        return str(self.__dict__)


class DucksboardPusher(object):

    def __init__(self, settings):
        self.settings = settings

    @property
    def widgets(self):
        widget_settings_path = path.join(self.settings.get("path"),
                                         "widgets_settings.yaml")
        try:
            with open(widget_settings_path, "r") as f:
                widgets = yaml.load(f.read())
        except IOError:
            raise exc.WidgetSettingsDoesNotExist
        else:
            from collect_project import collectors
            for widget in widgets:
                for endpoint in widget.endpoints:
                    try:
                        func_name = endpoint.collector.collector_func_name
                        getattr(collectors, func_name)
                    except AttributeError:
                        raise exc.CollectorDoesNotExist(func_name, widget)
            return widgets

    def push_value(self, eid, data):
        # We dont want to see the traceback on screen
        # so specif exception handling here
        #replace print by log message
        try:
            self.push_api_cli.push_value(id=str(eid),
                                         data=data)
        except Exception, e:
            print e.message

    def run(self, refresh_interval, collectors_timeout):
        while True:
            widget_threads = dict()
            endpoints_data = dict()
            for widget in self.widgets:
                widget_data = widget.collect_endpoints_data()
                endpoints_data.update(widget_data)

            for eid, data in endpoints_data.iteritems():
                thread = gevent.spawn(self.push_value,
                                      eid=str(eid),
                                      data=data)
                widget_threads["thread for endpoint %s" % eid] = thread
            time.sleep(refresh_interval)
            gevent.joinall(widget_threads.values())


def start_duckspush_project():
    parser = OptionParser(usage="usage: %prog [options] <project_name> <api_key>",
                          version="%prog 1.0")
    parser.add_option("-d", "--dashboard",
                      action="store",
                      dest="dashboard",
                      help="limit widgets collected to this dashboard",)
    parser.add_option("-l", "--limit",
                      action="store",
                      dest="limit",
                      help="Limit number of collected widgets",)

    (options, args) = parser.parse_args()

    if len(args) != 2:
        parser.error("wrong number of arguments")
        print parser.usage

    duckspush_settings_path = path.join(PROJECT_ROOT,
                                        "duckspush_settings.yaml")
    project_name = args[0]
    try:
        with open(duckspush_settings_path) as f:
            settings_data = f.read()
        proj = yaml.load(settings_data)["projects"].get(project_name)
    except IOError:
        pass
    else:
        if proj:
            raise exc.PushProjectAlreadyExist(project_name)

    api_key = args[1]
    dashboard_api_cli = api.get_api_cli(api_key, "dashboard")
    try:
        widgets_data = dashboard_api_cli.read_widgets()["data"]
    except HTTPError, e:
        if e.response.status_code == 401:
            raise exc.APITokenError

    filtered_widgets = []
    for w in widgets_data:
        widget = w["widget"]
        if widget["kind"].startswith("custom"):
            filtered_widgets.append(w)

    dashboard = options.dashboard
    if dashboard:
        try:
            dashboard_api_cli.read_dasboard(slug=dashboard)
        except HTTPError, e:
            if e.response.status_code == 401:
                raise exc.DashboardDoesNotExist(dashboard)

        dashboard_widgets = []
        for w in filtered_widgets:
            widget = w["widget"]
            if dashboard and widget["dashboard"] == dashboard:
                dashboard_widgets.append(w)
        filtered_widgets = dashboard_widgets

    limit = options.limit
    if limit:
        filtered_widgets = filtered_widgets[:limit]

    project_path = path.join(os.getcwd(), project_name)
    if os.path.exists(duckspush_settings_path):
        with open(duckspush_settings_path) as settings:
            settings_data = settings.read()
        settings_obj = yaml.load(settings_data)
        new_projects = settings_obj.get("projects")
        new_projects.update({project_name: {"path": project_path,
                                            "api_key": api_key}})
        settings_obj.update({"projects": new_projects})
    else:
        project_info = dict()
        project_info[project_name] = dict(path=project_path,
                                          api_key=api_key)

        settings_obj = dict(projects=project_info)

    with open(duckspush_settings_path, "w") as settings:
        settings_obj_str = yaml.dump(settings_obj)
        settings.write(settings_obj_str)

    utils.mkdir_p(project_path)
    open(path.join(project_path, "__init__.py"), "a").close()
    utils.generate_template("collectors.py", project_path)
    utils.generate_template("widgets_settings.yaml",
                            project_path,
                            widgets=filtered_widgets)


def delete_duckspush_project():
    parser = OptionParser(usage="usage: %prog <project_name>",
                          version="%prog 1.0")

    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("wrong number of arguments")
        print parser.usage

    duckspush_settings_path = path.join(PROJECT_ROOT,
                                        "duckspush_settings.yaml")
        
    try:
        with open(duckspush_settings_path) as f:
            settings_data = f.read()
        projects_settings = yaml.load(settings_data)
        project_name = args[0]
    except IOError:
        raise exc.PusherSettingsDoesNotExist
    
    try:
        project_path = projects_settings["projects"][project_name]["path"]
    except KeyError:
        raise exc.PushProjectDoesNotExist(project_name)
    
    del projects_settings["projects"][project_name]
    with open(duckspush_settings_path, "w") as f:
        write_data = yaml.dump(projects_settings)
        f.write(write_data)

    shutil.rmtree(project_path)

def run_pusher():
    parser = OptionParser(usage="usage: %prog [options] <project_name>",
                          version="%prog 1.0")
    parser.add_option("-pi", "--push-interval",
                      action="store",
                      dest="push_interval",
                      type="int",
                      default=30,
                      help="Push data interval => sec")
    parser.add_option("-ct", "--collectors_timeout",
                      action="store",
                      dest="timeout",
                      type="int",
                      default=20,
                      help="Timeout for data collection",)

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("wrong number of arguments")
        print parser.usage

    duckspush_settings_path = path.join(PROJECT_ROOT,
                                        "duckspush_settings.yaml")
    project_name = args[0]
    try:
        with open(duckspush_settings_path) as f:
            settings_data = f.read()
        proj_settings = yaml.load(settings_data)["projects"][project_name]
    except IOError:
        raise exc.PusherSettingsDoesNotExist
    except KeyError:
        raise exc.PushProjectDoesNotExist(project_name)

    sys.path.append(proj_settings.get("path"))
    pusher = DucksboardPusher(proj_settings)
    try:
        pusher.run(push_interval=options.push_interval,
                   collectors_timout=options.timeout)
        gevent.signal(signal.SIGQUIT, gevent.shutdown)
    except KeyboardInterrupt:
        print "Stopping pusher"


if __name__ == "__main__":
    #start_duckspush_project()
    delete_duckspush_project()
