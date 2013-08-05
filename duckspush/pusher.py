import gevent.monkey
gevent.monkey.patch_all()
import gevent
import api
import logging
import os
import signal
import sys
import time
import utils
import yaml

from duckspush import PACKAGE_ROOT
from os import path
from optparse import OptionParser
from requests import HTTPError
from shutil import rmtree
# logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
#                     level=logging.INFO)

formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
widget_logger = logging.getLogger("Widget")
pusher_logger = logging.getLogger("Pusher")
widget_logger.setLevel(logging.INFO)
widget_logger.addHandler(handler)
pusher_logger.setLevel(logging.INFO)
pusher_logger.addHandler(handler)


class Widget(yaml.YAMLObject):
    yaml_tag = u'!Widget'

    def __init__(self, wid, kind, title, dashboard, slots):
        self.wid = wid
        self.kind = kind
        self.title = title
        self.dashboard = dashboard
        self.slots = slots

    def collect_slots_data(self, timeout):
        slot_threads = [(slot.label, gevent.spawn(slot.collect_data))
                        for slot in self.slots]
        collected_data = {}
        for slot_label, st in slot_threads:
            try:
                collected_data[slot_label] = st.get(timeout=timeout)
            except Exception, e:
                if isinstance(e, AttributeError):
                    widget_logger.error("Widget<id=%s, title=%s, dashboard=%s> has no, or an incorrect datasource_func"
                                        % (self.id,
                                           self.title,
                                           self.dashboard,
                                           self.dashboard))
                collected_data[slot_label] = e
            except gevent.Timeout, t:
                collected_data[slot_label] = t
        # threads = [s[1] for s in slot_threads]
        # for t in threads:
        #     t.join(timeout=timeout)
        #gevent.joinall([s[1] for s in slot_threads], timeout=timeout)
        return collected_data


class Slot(yaml.YAMLObject):
    yaml_tag = u'!Slot'

    def __init__(self, subtitle, label, datasource_func):
        self.subtitle = subtitle
        self.label = label
        self.datasource_func = datasource_func

    def collect_data(self):
        try:
            return self.datasource_func()
        except Exception, e:
            return e


class DataSourceFunc(yaml.YAMLObject):
    yaml_tag = u'!DataSourceFunc'

    def __init__(self, func_name, func_kwargs):
        self.func_name = func_name
        self.func_kwargs = func_kwargs

    def __call__(self):
        import datasources
        func = getattr(datasources, self.func_name)
        return func(**self.func_kwargs)


class DucksboardPusher(object):

    def __init__(self, settings):
        self.settings = settings

    @property
    def widgets(self):
        widget_settings_path = path.join(self.settings.get("path"),
                                         "widgets_settings.yaml")
        with open(widget_settings_path, "r") as f:
            widgets = yaml.load(f.read())
        return widgets

    def collect_widgets_data(self, timeout):
        widget_threads = [(w, gevent.spawn(w.collect_slots_data, timeout))
                          for w in self.widgets]
        all_data = dict()
        for widget, wt in widget_threads:
            data = wt.get()
            print data.values()[0]
            if isinstance(data.values()[0], (Exception, gevent.Timeout)):
                print "xxxxxxxxxxxxxxxxxxx"
                print data
                print "xxxxxxxxxxxxxxxxxxx"
                pusher_logger.error("Widget<id=%s, title=%s, dashboard=%s>, failed to collect data. Error ==> %s" 
                                    % (widget.id,
                                       widget.title,
                                       widget.dashboard,
                                       data))
            else:
                pusher_logger.info("Widget<id=%s, title=%s, dashboard=%s>, collected data  ==> %s" 
                                   % (widget.id,
                                      widget.title,
                                      widget.dashboard,
                                      data))

                all_data.update(data)
        return all_data

    def push_to_ducksboard(self, collected_data):
        push_threads = [gevent.spawn(self.push_api_cli.push_value,
                                     id=slot_label,
                                     data=data)
                        for slot_label, data in collected_data.iteritems()
                        if not isinstance(data, Exception)]
        gevent.joinall(push_threads)
        pusher_logger.info("All collected_data pushed to ducksboard")

    def run(self, push_interval, collectors_timeout):
        while True:
            collected_data = self.collect_widgets_data(collectors_timeout)
            self.push_to_ducksboard(collected_data)
            time.sleep(push_interval)


def start_push_project():
    parser = OptionParser(
        usage="usage: %prog [options] <project_name> <api_key>",
        version="%prog 1.0")
    parser.add_option("-d", "--dashboard",
                      action="store",
                      dest="dashboard",
                      help="limit widgets collected to this dashboard",)
    parser.add_option("-l", "--limit",
                      action="store",
                      type="int",
                      dest="limit",
                      help="Limit number of collected widgets",)

    (options, args) = parser.parse_args()

    if len(args) != 2:
        parser.error("wrong number of arguments")
        print parser.usage

    duckspush_settings_path = path.join(PACKAGE_ROOT,
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
            sys.exit("A project already exist under this name.Please choose an other one")

    api_key = args[1]
    dashboard_api_cli = api.get_api_cli(api_key, "dashboard")
    # Trying to get custom widgets for this api key
    try:
        widgets_data = dashboard_api_cli.read_widgets()["data"]
    except HTTPError, e:
        if e.response.status_code == 401:
            sys.exit("It seems that the key %s is incorrect.Please set a correct api" % api_key)
    else:
        filtered_widgets = [w for w in widgets_data
                            if w["widget"]["kind"].startswith("custom")]

    dashboard = options.dashboard
    # Check dashboard existence
    if dashboard:
        try:
            dashboard_api_cli.read_dashboard(slug=dashboard)
        except HTTPError, e:
            if e.response.status_code == 404:
                sys.exit("Sorry can't find any dashboad under the name of: %s" % dashboard)
        # Then filtered already grabbed widgets
        filtered_widgets = [w for w in filtered_widgets
                            if w["widget"]["dashboard"] == dashboard]

    # If limit is set return a slice of widgets
    limit = options.limit
    if limit:
        filtered_widgets = filtered_widgets[:limit]

    project_path = path.join(os.getcwd(), project_name)
    if os.path.exists(duckspush_settings_path):
        with open(duckspush_settings_path) as settings:
            settings_data = settings.read()
        settings_obj = yaml.load(settings_data)
    else:
        settings_obj = dict(projects={})

    settings_obj["projects"][project_name] = dict(path=project_path,
                                                  api_key=api_key)
    # Write setings back to duckspush conf
    with open(duckspush_settings_path, "w") as settings:
        settings_obj_str = yaml.dump(settings_obj)
        settings.write(settings_obj_str)

    # Build project environnement
    utils.mkdir_p(project_path)
    open(path.join(project_path, "__init__.py"), "a").close()
    utils.generate_template("datasources.py", project_path)
    utils.generate_template("widgets_settings.yaml",
                            project_path,
                            widgets=filtered_widgets)


def remove_push_project():
    parser = OptionParser(usage="usage: %prog <project_name>",
                          version="%prog 1.0")

    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("wrong number of arguments")
        print parser.usage

    duckspush_settings_path = path.join(PACKAGE_ROOT,
                                        "duckspush_settings.yaml")

    with open(duckspush_settings_path) as f:
        settings_data = f.read()

    projects_settings = yaml.load(settings_data)
    project_name = args[0]
    try:
        project_path = projects_settings["projects"][project_name]["path"]
    except KeyError:
        sys.exit("Project %s does not exists" % project_name)
    del projects_settings["projects"][project_name]
    with open(duckspush_settings_path, "w") as f:
        write_data = yaml.dump(projects_settings)
        f.write(write_data)
    rmtree(project_path)


def run_pusher():
    parser = OptionParser(usage="usage: %prog [options] <project_name>",
                          version="%prog 1.0")
    parser.add_option("-p", "--push-interval",
                      action="store",
                      dest="push_interval",
                      type="int",
                      default=30,
                      help="Push data interval => sec")
    parser.add_option("-c", "--collectors_timeout",
                      action="store",
                      dest="timeout",
                      type="int",
                      default=10,
                      help="Timeout for data collection",)

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("wrong number of arguments")
        print parser.usage

    duckspush_settings_path = path.join(PACKAGE_ROOT,
                                        "duckspush_settings.yaml")
    project_name = args[0]
    with open(duckspush_settings_path) as f:
        settings_data = f.read()
    try:
        proj_settings = yaml.load(settings_data)["projects"][project_name]
    except KeyError:
        sys.exit("Project %s does not exists" % project_name)

    sys.path.append(proj_settings.get("path"))
    pusher = DucksboardPusher(proj_settings)
    pusher.push_api_cli = api.get_api_cli(proj_settings.get("api_key"),
                                          "push")
    try:
        pusher.run(push_interval=options.push_interval,
                   collectors_timeout=options.timeout)
        gevent.signal(signal.SIGQUIT, gevent.shutdown)
    except KeyboardInterrupt:
        pusher_logger.info("Stopping pusher")

if __name__ == "__main__":
    start_push_project()
    
