import time
from kubernetes import watch
from kubernetes.client.exceptions import ApiException


class KubernetesLogStreamer:
    def __init__(self, core_v1_api, namespace: str):
        self._core = core_v1_api
        self._namespace = namespace

    def _wait_for_pod(self, job_name: str, timeout: int = 60):
        for _ in range(timeout):
            pods = self._core.list_namespaced_pod(
                namespace=self._namespace, label_selector=f"job-name={job_name}"
            )
            if pods.items:
                pod = pods.items[0]
                if pod.status.phase in ["Running", "Succeeded", "Failed"]:
                    return pod.metadata.name
            time.sleep(1)
        raise TimeoutError("❌ Pod did not appear within timeout.")

    def _stream_container_logs(self, pod_name: str, container_name: str):
        w = watch.Watch()
        try:
            for line in w.stream(
                self._core.read_namespaced_pod_log,
                name=pod_name,
                namespace=self._namespace,
                container=container_name,
                follow=True,
                _preload_content=False,
            ):
                print(
                    line.strip()
                    if isinstance(line, str)
                    else line.decode("utf-8").strip()
                )
        except ApiException as e:
            print(
                f"⚠️ Failed to stream logs from container '{container_name}': {e.reason}"
            )
        except Exception as e:
            print(
                f"⚠️ Unexpected error while reading logs from '{container_name}': {str(e)}"
            )

    def stream_logs(self, job_name: str):
        pod_name = self._wait_for_pod(job_name)
        pod = self._core.read_namespaced_pod(name=pod_name, namespace=self._namespace)

        # pod order : init containers → main containers
        containers = []

        if pod.spec.init_containers:
            containers.extend(pod.spec.init_containers)

        if pod.spec.containers:
            containers.extend(pod.spec.containers)

        for container in containers:
            print(f"\n📦 Logs from container: {container.name}")
            self._stream_container_logs(pod_name, container.name)
