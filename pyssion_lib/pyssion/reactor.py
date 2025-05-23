from .core import Pyssion
from .handler.error_handler import error_wrapper
from .reactor_extension.service import make_service


class Reactor(Pyssion):
    def __init__(self):
        super().__init__()

    @error_wrapper
    def run(self):
        print("test")
        make_service()
