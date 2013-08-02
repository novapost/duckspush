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
import yaml

from ducksboard_publisher import PROJECT_ROOT
#from jinja2 import Environment, PackageLoader
from os import path


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


class DucksboardPublisher(object):

    def __init__(self):
        self.push_api_cli = api.get_api_cli(
            api_key=self.settings.get("DUCKSBOARD_API_TOKEN"),
            api_name="push")

    def init_collector_project(self):
        project_path = path.join(PROJECT_ROOT, "collect_project")
        utils.mkdir_p(project_path)
        try:
            init_file_path = path.join(project_path, "__init__.py")
            open(init_file_path, 'a').close()

            utils.generate_template("collectors.py")

            api_key = self.settings.get("DUCKSBOARD_API_TOKEN")
            dashboard_api_cli = api.get_api_cli(api_key, "dashboard")
            # handle exception in case of wrong api token publisher settings
            widget_data = dashboard_api_cli.read_widgets()["data"]
            custom_widgets = []

            for w in widget_data:
                kind = w["widget"]["kind"]
                if kind.startswith("custom"):
                    custom_widgets.append(w)
            utils.generate_template("widget_settings.yaml",
                                    widget_data=custom_widgets)
        except Exception, e:
        # replace by specific handled exception
            shutil.rmtree(project_path)
            raise e

    @property
    def settings(self):
        settings_path = path.join(PROJECT_ROOT, "publisher_settings.yaml")
        try:
            with open(settings_path, "r") as config_file:
                settings = yaml.load(config_file.read())
        except IOError:
            raise exc.PublisherSettingsDoesNotExist
        else:
            return settings

    @property
    def widgets(self):
        config_path = path.join(PROJECT_ROOT,
                                "collect_project",
                                "widget_settings.yaml")
        try:
            with open(config_path, "r") as config_file:
                widgets = yaml.load(config_file.read())
        except IOError:
            raise exc.CollectorProjectDoesNotExist
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

    def run(self):
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
            time.sleep(self.settings.get("PUBLISHER_REFRESH_INTERVAL"))
            gevent.joinall(widget_threads.values())


def run_publisher():
    publisher = DucksboardPublisher()
    try:
        publisher.run()
        gevent.signal(signal.SIGQUIT, gevent.shutdown)
    except KeyboardInterrupt:
        print "Stopping publisher"


def init_publisher_settings():
    pub_settings_path = path.join(PROJECT_ROOT, "publisher_settings.yaml")
    if not os.path.exists(pub_settings_path):
        utils.generate_template("publisher_settings.yaml")


def init_collect_project():
    publisher = DucksboardPublisher()
    publisher.init_collector_project()
