class ApiDoesNotExist(Exception):
    pass


class CollectorDoesNotExist(Exception):
    def __init__(self, func_name, widget):
        self.func_name = func_name
        self.widget = widget

    def __str__(self):
        return "Collector: \"%s\" not found for Widget: %s" % (self.func_name,
                                                               self.widget)


class PusherSettingsDoesNotExist(Exception):
    def __init__(self, project_name):
        self.project_name = project_name

    def __str__(self):
        return "Pusher settings not found"


class WidgetSettingsDoesNotExist(Exception):
    def __init__(self, project_name):
        self.project_name = project_name

    def __str__(self):
        return "Widget settings not found for: \"%s\"" % self.project_name


class DashboardDoesNotExist(Exception):
    def __init__(self, dashboard_name):
        self.dashboard_name = dashboard_name

    def __str__(self):
        return "Dashboard: \"%s\" not found" % self.dashboard_name


class PushProjectDoesNotExist(Exception):
    def __init__(self, project_name):
        self.project_name = project_name

    def __str__(self):
        return "Project: \"%s\" not found" % self.project_name


class PushProjectAlreadyExist(Exception):
    def __init__(self, project_name):
        self.project_name = project_name

    def __str__(self):
        return "Project: \"%s\" already exists" % self.project_name


class APITokenError(Exception):
    def __str__(self):
        return "Invalid api token"
