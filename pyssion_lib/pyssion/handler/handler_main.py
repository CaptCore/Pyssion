import sys
import traceback


class OriginPyssion:
    def __init__(self):
        self.name = "Pyssion"

    def _handle_error(self, exception: Exception):
        print(f"[{self.name} ERROR]: {exception!r}")
        print("-" * 60)
        traceback.print_exc()
        print("-" * 60)
        sys.exit(1)
