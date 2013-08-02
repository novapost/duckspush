class ApiDoesNotExist(Exception):
    pass


class CollectorDoesNotExist(Exception):
    def __init__(self, func_name, widget):
        self.func_name = func_name
        self.widget = widget

    def __str__(self):
        return "Collector: \"%s\" not found for Widget: %s" % (self.func_name,
                                                               self.widget)


class CollectorProjectDoesNotExist(Exception):
    def __str__(self):
        return "Please start a collector project before runing publisher"


class PublisherSettingsDoesNotExist(Exception):
    def __str__(self):
        return "Unable to find the publisher settings file"
