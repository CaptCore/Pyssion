# pyssion/k8s_client.py
from kubernetes import client, config
from kubernetes.client import Configuration
from kubernetes.client.rest import ApiException
from pyssion.runner.k8s_container import pyssion_job_container, timer, logviewer, create_configmap_from_file
from pyssion.handler.error_handler import error_wrapper
from pyssion.handler.handler_main import origin_pyssion


class KubernetesJobLauncher(origin_pyssion):
    """
    Launch Kubernetes Jobs with optional PersistentVolumeClaim support and MinIO pre-download logic.
    """
    def __init__(
        self,
        image: str,
        job_name: str,
        namespace: str,
        minio_env: dict,
        resource: client.V1ResourceRequirements,
        cache: bool = False,
        req_file: str = None,
        config_file: str = None,
        ssl_ignore: bool = False
    ):
        """
        :param image: Container image for the Job.
        :param job_name: Unique Kubernetes Job name.
        :param namespace: Kubernetes namespace.
        :param minio_env: Environment vars for MinIO access.
        :param resource: Pod resource limits/requests.
        :param req_file: (Optional) requirements file path under /app/code.
        :param config_file: (Optional) kubeconfig file path.
        :param ssl_ignore: Set True to disable SSL verification.
        """
        super().__init__()
        self.image = image
        self.job_name = job_name
        self.namespace = namespace
        self.minio_env = minio_env
        self.resource = resource
        self.req_file = f"/app/code/{req_file}" if req_file else None

        # Load Kubernetes configuration once
        if config_file:
            config.load_kube_config(config_file=config_file)
        else:
            config.load_kube_config()

        # Configure SSL verification
        conf = Configuration.get_default_copy()
        conf.verify_ssl = not ssl_ignore
        Configuration.set_default(conf)

        # API clients
        self.core_v1 = client.CoreV1Api()
        self.batch_v1 = client.BatchV1Api()
        self.storage_v1 = client.StorageV1Api()

    @error_wrapper
    def launch(self, warn_ignore: bool):
        """
        Create and run a Kubernetes Job, then stream its logs.
        :param warn_ignore: If True, suppress specific warnings during job wait.
        """
        # Build environment variables for container
        # Generate the shell script for MinIO download + execution
        # Container spec
        container, volume = pyssion_job_container(self.minio_env,image=self.image, req_file=self.req_file)

        # Pod template spec
        pod_spec = client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=[volume]
        )
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"job-name": self.job_name}),
            spec=pod_spec
        )

        # Job spec
        job_spec = client.V1JobSpec(template=template, backoff_limit=0)
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=self.job_name),
            spec=job_spec
        )

        # Create and monitor the Job
        self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
        print(f"🚀 Kubernetes Job launched: {self.job_name}")

        status = timer(self.namespace, self.job_name, warn_ignore)
        logviewer(self.namespace, self.job_name)
        print(f"Job status: {status}")

    @error_wrapper
    def _create_pvc(
        self,
        name: str,
        namespace: str = "default",
        storage_class: str = "nfs-client",
        access_modes: tuple = ("ReadWriteMany",),
        size: str = "10Gi"
    ):
        """
        Ensure a PersistentVolumeClaim exists, creating it if necessary.
        """
        if self._pvc_exists(name,namespace):
            pvc_manifest = client.V1PersistentVolumeClaim(
                metadata=client.V1ObjectMeta(name=name),
                spec=client.V1PersistentVolumeClaimSpec(
                    access_modes=list(access_modes),
                    storage_class_name=storage_class,
                    resources=client.V1ResourceRequirements(requests={"storage": size})
                )
            )
            try:
                self.core_v1.create_namespaced_persistent_volume_claim(
                    namespace=namespace,
                    body=pvc_manifest
                )
                print(f"✅ PVC '{name}' created in namespace '{namespace}'.")
                return True
            except ApiException as e:
                if e.status == 409:
                    print(f"ℹ️ PVC '{name}' already exists in namespace '{namespace}'.")
                else:
                    raise RuntimeError("Can't Get Kubernetes's Normal Response.")
        else:
            return True
    
    @error_wrapper
    def _pvc_exists(
    self,
    name: str, 
    namespace: str = "default"
    ) -> bool:
        """
            find cache's persistent volume claim function
        """
        try:
            self.storage_v1.read_namespaced_persistent_volume_claim(name, namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            else:
                raise RuntimeError("Can't Get Kubernetes's Normal Response.")
