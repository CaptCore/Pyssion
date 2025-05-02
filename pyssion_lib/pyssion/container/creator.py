from kubernetes import client
from pyssion.container.builder import main_container_build,init_container_build
from pyssion.manager.namespace import Pyssion_Namespace
from pyssion.handler.handler_main import origin_pyssion


class KubernetesJobCreator(origin_pyssion):
    def __init__(
        self,
        image: str,
        namespace: str,
        nametag: Pyssion_Namespace,
        minio_env: dict,
        resource: client.V1ResourceRequirements = None,
        req_file: str = None,
        entrypoint_file:str = None,
        venv_cache:bool = False
    ):
        #container type setup
        self._image = image

        #nametag
        self._job_name = nametag.job_name
        self._volume_name = nametag.volume_name
        self._pvc_name = nametag.pvc_name

        #kubernetes container setup
        self._namespace = namespace
        self._resource = resource or None

        #command setup
        self._req_file = req_file if req_file else None
        self._entrypoint_file = entrypoint_file or None
        self._venv_cache = venv_cache

        #container env setup
        self._minio_env = minio_env

    def build_job_spec(self) -> client.V1Job:
        print(f"req file : {self._req_file}")
        job_list = []
        volume_list = []

        print(f"❕{self._minio_env["MINIO_BUCKET"]}/{self._minio_env["MINIO_PREFIX"]} will be copy on your container")
        container, volume = init_container_build(self._minio_env,self._volume_name,self._pvc_name)
        job_list.append(container)
        volume_list.append(volume)

        job_list.append(main_container_build(
            volume_name=self._volume_name,
            image=self._image,
            req_file=self._req_file,
            resources=self._resource,
            entrypoint_file=self._entrypoint_file,
            venv_cache=self._venv_cache
        ))

        pod_spec = client.V1PodSpec(
            restart_policy="Never",
            containers=job_list,
            volumes=volume_list
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
