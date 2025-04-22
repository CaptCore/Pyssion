# pyssion/k8s_client.py
import os
from pathlib import Path
from kubernetes import client, config
from kubernetes.client import Configuration
from kubernetes.client.rest import ApiException
from pyssion.runner.k8s_container import pyssion_job_container, timer, logviewer
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
        self.name = "Kubernetes Job Launcher"
        self._image = image
        self._job_name = job_name
        self._namespace = namespace
        self._minio_env = minio_env
        self._resource = resource
        self._req_file = f"/app/code/{req_file}" if req_file else None

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
        self._core_v1 = client.CoreV1Api()
        self._batch_v1 = client.BatchV1Api()
        self._storage_v1 = client.StorageV1Api()

    @error_wrapper
    def launch(self, warn_ignore: bool):
        """
        Create and run a Kubernetes Job, then stream its logs.
        :param warn_ignore: If True, suppress specific warnings during job wait.
        """
        # Kubernetes pod spec list
        volumes, volume_mounts, containers = [],[],[]
        # PVC name 
        pvc_name = f"{self._job_name}-data"
        
        # Build environment variables for container
        # Generate the shell script for MinIO download + execution
        # Container spec

        
        
        try:
            self._create_configmap_from_file()
        except:
            print("Can't Create Config Map")
        container, volume = pyssion_job_container(self._minio_env,image=self._image, req_file=self._req_file)

        if self._create_pvc(
                name=pvc_name,
                namespace=self._namespace,
                storage_class="longhorn",
                access_modes=("ReadWriteOnce",),
                size="100Gi"
            ):
            print(f"👌 Create PVC")
        else:
            print(f"🚨 Can't Get PVC data")

        volumes.append(
                client.V1Volume(
                    name="data",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=pvc_name
                    )
                )
            )

        volume_mounts.append(
                client.V1VolumeMount(
                    name="data",
                    mount_path="/app/code"
                )
            )
        # Update volume List
        volumes.append(volume)
        # Update container
        container.volume_mounts = (container.volume_mounts or []) + volume_mounts
        # Update container List
        containers.append(container)
        
        # Pod template spec
        pod_spec = client.V1PodSpec(
            restart_policy="Never",
            containers=containers,
            volumes=volumes
        )
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"job-name": self._job_name}),
            spec=pod_spec
        )

        # Job spec
        job_spec = client.V1JobSpec(template=template, backoff_limit=0)
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=self._job_name),
            spec=job_spec
        )

        # Create and monitor the Job
        self._batch_v1.create_namespaced_job(namespace=self._namespace, body=job)
        print(f"🚀 Kubernetes Job launched: {self._job_name}")

        status = timer(self._namespace, self._job_name, warn_ignore)
        logviewer(self._namespace, self._job_name)
        print(f"Job status: {status}")
        
    @error_wrapper
    def _create_configmap_from_file(self):
        """
        Create or update a ConfigMap containing the runner script.
        Uses self.job_name as the ConfigMap name and self.namespace for the namespace.
        """
        from kubernetes.client.rest import ApiException
        pkg_dir = Path(__file__).parent
        script_path = pkg_dir / "runner_container" / "k8s_uploader.py"

        if not script_path.exists():
            raise FileNotFoundError(f"ConfigMap source file not found: {script_path}")

        script_content = script_path.read_text(encoding="utf-8")
        configmap_name = self._job_name
        namespace = self._namespace

        cm_body = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(name=configmap_name, namespace=namespace),
            data={script_path.name: script_content}
        )

        try:
            # already Exist, than patch
            self._core_v1.read_namespaced_config_map(configmap_name, namespace)
            self._core_v1.patch_namespaced_config_map(
                name=configmap_name,
                namespace=namespace,
                body=cm_body
            )
            print(f"🔄 Updated ConfigMap '{configmap_name}' in namespace '{namespace}'.")
        except ApiException as e:
            if e.status == 404:
                # Can't Find, than create
                self._core_v1.create_namespaced_config_map(
                    namespace=namespace,
                    body=cm_body
                )
                print(f"✅ Created ConfigMap '{configmap_name}' in namespace '{namespace}'.")
            else:
                # Another Error, Raise
                raise

        return cm_body
    
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
        if self._pvc_exists(name,namespace) == False:
            pvc_manifest = client.V1PersistentVolumeClaim(
                metadata=client.V1ObjectMeta(name=name),
                spec=client.V1PersistentVolumeClaimSpec(
                    access_modes=list(access_modes),
                    storage_class_name=storage_class,
                    resources=client.V1ResourceRequirements(requests={"storage": size})
                )
            )
            try:
                self._core_v1.create_namespaced_persistent_volume_claim(
                    namespace=namespace,
                    body=pvc_manifest
                )
                print(f"✅ PVC '{name}' created in namespace '{namespace}'.")
                return True
            except ApiException as e:
                if e.status == 409:
                    print(f"ℹ️ PVC '{name}' already exists in namespace '{namespace}'.")
                    return False
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
            self._core_v1.read_namespaced_persistent_volume_claim(name, namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            else:
                raise RuntimeError("Can't Get Kubernetes's Normal Response.")
    
