from kubernetes import client
from pyssion.runner.k8s_container_controller import pyssion_job_container
from pyssion.handler.handler_main import origin_pyssion


class KubernetesJobCreator(origin_pyssion):
    def __init__(
        self,
        image: str,
        job_name: str,
        namespace: str,
        resource: client.V1ResourceRequirements = None,
        req_file: str = None
    ):
        self._image = image
        self._job_name = job_name
        self._namespace = namespace
        self._resource = resource or None
        self._req_file = f"/app/code/{req_file}" if req_file else None

    def build_job_spec(self) -> client.V1Job:
        container, config_volume = pyssion_job_container(
            pyssion_configmap_name=self._job_name,
            image=self._image,
            req_file=self._req_file,
            resources=self._resource
        )

        pod_spec = client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=[config_volume]
        )

        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"job-name": self._job_name}),
            spec=pod_spec
        )

        return client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=self._job_name),
            spec=client.V1JobSpec(template=template, backoff_limit=0)
        )
