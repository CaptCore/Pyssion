from kubernetes import client
from pathlib import Path


def create_configmap_from_directory(
    configmap_name,
    directory: Path,
    modified_entrypoint: Path = None,
    namespace="default",
):
    data = {}

    for path in directory.rglob("*.py"):
        if path.is_file():
            rel_path = path.relative_to(directory).as_posix()
            if modified_entrypoint and path.samefile(modified_entrypoint):
                content = modified_entrypoint.read_text(encoding="utf-8")
            else:
                content = path.read_text(encoding="utf-8")
            data[rel_path] = content

    configmap = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name=configmap_name), data=data
    )

    api = client.CoreV1Api()
    api.create_namespaced_config_map(namespace=namespace, body=configmap)
