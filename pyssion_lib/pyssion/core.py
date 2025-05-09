from pyssion.manager.namespace import Pyssion_Namespace
from pyssion.handler.handler_main import origin_pyssion
from pyssion.container.creator import KubernetesJobCreator
from pyssion.handler.error_handler import error_wrapper
from pyssion.manager.client import KubernetesClientManager
from pyssion.manager.cleaner import KubernetesJobCleaner
from pyssion.manager.logger import KubernetesLogStreamer
from pyssion.manager.envloader import get_env
from pyssion.saver.minio_client import MinioUploader
from pyssion.container.builder import PVCBuilder, PVCManager
from pyssion.container.util import delete_pvc_and_pv, status_print


class Pyssion(origin_pyssion):
    def __init__(self):
        env = get_env()
        # set Pyssion Workload init
        self.name = "Pyssion Core"
        self._namespace = Pyssion_Namespace()

        # env build
        self._k8s_config = env.get_k8s_config()
        self._minio_config = env.get_minio_config()
        self._entrypoint_file = env.get_entrypoint()
        self._req_file = env.get_req_file()
        self._resource_config = env.get_gpu_resource()
        self._ssl_ignore = env.get_ssl_ignore()
        self._pvc_size = env.get_pvc_storage()
        self._venv_cache = env.use_venv_cache()
        self._cache_drop = env.delete_pvc_after_job()
        self._minio_config["MINIO_PREFIX"] = self._namespace.pyssion_unique_name

        # kubernetes namespace -> get from env
        self._kubernetes_namespace = self._k8s_config.get("namespace", "default")

        # Kubernetes load
        self._client_manager = KubernetesClientManager(
            self._k8s_config, ssl_ignore=self._ssl_ignore
        )
        self._client_manager.configure()
        self._batch_v1, self._core_v1, self._storage_v1 = (
            self._client_manager.get_clients()
        )

        # Kubernetes Manage
        self._job_cleaner = KubernetesJobCleaner(self._batch_v1)
        self._log_streamer = KubernetesLogStreamer(
            self._core_v1, self._kubernetes_namespace
        )

    @error_wrapper
    def run(self):
        print("✅ pyssion Fission!")
        self._job_cleaner.delete_if_exists(
            self._kubernetes_namespace, self._namespace.job_name
        )

        print("Upload Local File to MinIO!")
        uploader = MinioUploader(self._minio_config)
        uploader.upload_project(self._namespace.project_dir)

        print("✅ Get Pyssion Config Data!")
        print(f"👌Pyssion job name : {self._namespace.job_name}")
        print("✅ Create PVC")

        pvc = PVCBuilder(
            pvc_name=self._namespace.pvc_name, storage=self._pvc_size
        ).build()
        pvc_manager = PVCManager(self._core_v1, self._kubernetes_namespace)
        pvc_manager.ensure_or_resize(pvc)

        print("✅ Create Kubernetes Job")
        job_spec = KubernetesJobCreator(
            image="python",
            minio_env=self._minio_config,
            namespace=self._kubernetes_namespace,
            nametag=self._namespace,
            resource=self._resource_config,
            req_file=self._req_file,
            entrypoint_file=self._entrypoint_file,
            venv_cache=self._venv_cache,
        ).build_job_spec()

        self._batch_v1.create_namespaced_job(
            namespace=self._kubernetes_namespace, body=job_spec
        )
        self._log_streamer.stream_logs(self._namespace.job_name)

        status_print(
            self._batch_v1, self._kubernetes_namespace, self._namespace.job_name
        )

        if self._cache_drop == True:
            self._job_cleaner.delete_if_exists(
                self._kubernetes_namespace, self._namespace.job_name
            )
            delete_pvc_and_pv(
                self._core_v1, self._kubernetes_namespace, self._namespace.pvc_name
            )
        else:
            print("✅ pyssion job Finished!")
