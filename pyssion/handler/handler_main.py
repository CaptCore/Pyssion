import sys
class origin_pyssion:
    def __init__(self):
        self.name = "Pyssion"
    def _handle_error(self, exception: Exception):
        print(f"[{self.name} ERROR]: {exception!r}")
        sys.exit(1)