def error_wrapper(method):
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as e:
            self._handle_error(e)
    return wrapper

def warn_ignore(method):
    def warn_wrapper(self, *args, **kwargs):
        from urllib3.exceptions import InsecureRequestWarning
        from urllib3 import disable_warnings
        disable_warnings(InsecureRequestWarning)
    return warn_wrapper
