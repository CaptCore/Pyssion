class ResourceConfigurator:
    def __init__(self, gpus: int = None):
        self._gpus = gpus

    def get_config(self):
        if self._gpus is not None:
            return {
                "requests": {"nvidia.com/gpu": str(self._gpus)},
                "limits": {"nvidia.com/gpu": str(self._gpus)}
            }
        return None