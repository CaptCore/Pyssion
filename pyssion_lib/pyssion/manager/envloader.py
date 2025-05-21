# pyssion/manager/envloader.py
from pathlib import Path
import shlex
import inspect
from .resource import ResourceConfigurator

_cached_env = None

def get_env():
    global _cached_env
    if _cached_env is None:
        _cached_env = PyssionEnvLoader()
    return _cached_env


def reset_env():
    global _cached_env
    _cached_env = None


class PyssionEnvLoader:
    def __init__(self):
        self.config = {}
        self.env_file = self._resolve_env_file()
        if self.env_file:
            self._load()
        else:
            print("⚠️ .pyssionenv not found. Continuing without environment overrides.")

    def _resolve_env_file(self):
        base_path = Path(inspect.stack()[-1].filename).resolve().parent
        candidate = base_path / ".pyssionenv"
        if candidate.exists():
            return candidate
        fallback = Path.home() / ".pyssionenv"
        return fallback if fallback.exists() else None

    def _load(self):
        with open(self.env_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export ") :]
                if "=" in line:
                    key, value = line.split("=", 1)
                    self.config[key.strip()] = shlex.split(value.strip())[0]

    def get_minio_config(self):
        return {
            "MINIO_ENDPOINT": self.config.get("MINIO_ENDPOINT"),
            "MINIO_ACCESS": self.config.get("MINIO_ACCESS"),
            "MINIO_SECRET": self.config.get("MINIO_SECRET"),
            "MINIO_BUCKET": self.config.get("MINIO_BUCKET"),
        }

    def get_k8s_config(self):
        return {
            "config_file": self.config.get("K8S_CONFIG"),
            "namespace": self.config.get("K8S_NAMESPACE", "default"),
        }

    def get_entrypoint(self):
        return self.config.get("ENTRYPOINT_FILE")

    def get_req_file(self):
        return self.config.get("REQ_FILE")

    def get_gpu_resource(self):
        return ResourceConfigurator(self.config.get("GPU")).get_config()

    def get_ssl_ignore(self) -> bool:
        val = self.config.get("SSL_IGNORE", "true").lower()
        return val in ["1", "true", "yes", "on"]

    def get_pvc_storage(self, default: str = "128Gi") -> str:
        return self.config.get("PVC_STORAGE", default)

    def use_venv_cache(self) -> bool:
        return self.config.get("USE_VENV_CACHE", "0").strip() in ["1", "true", "yes"]

    def delete_pvc_after_job(self) -> bool:
        return self.config.get("DELETE_PVC_AFTER_JOB", "0").strip() in [
            "1",
            "true",
            "yes",
        ]
