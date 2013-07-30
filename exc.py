class ApiDoesNotExist(Exception):
    pass

class CollectorDoesNotExist(Exception):
    
    def __init__(self, func_name, widget):
        self.func_name = func_name
        self.widget = widget

    def __str__(self):
        return "Collector: \"%s\" not found for Widget: %s" % (self.func_name,
                                                              self.widget)
