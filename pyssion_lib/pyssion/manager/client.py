# pyssion/manager/client.py
from kubernetes import client, config
from kubernetes.client import Configuration


class KubernetesClientManager:
    def __init__(self, k8s_config: dict = None, ssl_ignore: bool = True):
        self.k8s_config = k8s_config
        self.ssl_ignore = ssl_ignore
        self._configured = False

    def configure(self):
        config_path = self.k8s_config.get("config_file") if self.k8s_config else None

        if config_path:
            print(f"🔧 Using kubeconfig: {config_path}")
            config.load_kube_config(config_file=config_path)
        else:
            print("🔧 Using default kubeconfig")
            config.load_kube_config()

        conf = Configuration.get_default_copy()
        conf.verify_ssl = self.ssl_ignore
        Configuration.set_default(conf)

        self._configured = True

    def get_clients(self):
        if not self._configured:
            raise RuntimeError(
                "Kubernetes client is not configured. Call `configure()` first."
            )

        return (
            client.BatchV1Api(),
            client.CoreV1Api(),
            client.StorageV1Api(),
        )
