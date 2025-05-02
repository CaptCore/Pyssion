# pyssion/core.py
import time
from pathlib import Path
from kubernetes import client, config, watch
from kubernetes.client import Configuration
from kubernetes.client.exceptions import ApiException

from pyssion.core_util.path_util import Pyssion_Namespace
from pyssion.handler.handler_main import origin_pyssion
from pyssion.runner.k8s_job_creator import KubernetesJobCreator
from pyssion.handler.error_handler import error_wrapper

class Pyssion(origin_pyssion):
    def __init__(self, k8s_config:dict, minio_config:dict = None, entrypoint_file:str=None, req_file:str=None, gpus:int=None, fast_use:bool=False):
        """
        Pyssion's Core Class
        For run Pyssion, You must declare this class on your code.
        """
        self.name = "Pyssion Core"
        self._Pyssion_namespace = Pyssion_Namespace()
        self._minio_config = minio_config or None
        self._k8s_config = k8s_config or None
        self._kubernetes_namespace = self._k8s_config.get("namespace", "default")
        self._entrypoint_file = entrypoint_file or None
        self._req_file = req_file or None
        self._gpus = self._gpu_resources(gpus) or None
        self._fast_use = fast_use or None

    @error_wrapper
    def run(self):
        print("✅ pyssion Fission!")
        self.kuberenetes_config(self._k8s_config)
        if self._delete_k8s_job(self._kubernetes_namespace,self._Pyssion_namespace.job_name):
            print("🗑️ Delete pre k8s Job")
        print("✅ Get Pyssion Config Data!")
        print(f"Pyssion job name : {self._Pyssion_namespace.job_name}")
        print("✅ Create PVC")
        
        self._create_configmap_with_zipped_code()
        job_launcher = KubernetesJobCreator(
            image="python",
            namespace=self._kubernetes_namespace,
            resource=self._gpus,
            req_file=self._req_file,
            entrypoint_file=self._entrypoint_file
        ).build_job_spec()
        self._batch_v1.create_namespaced_job(namespace=self._kubernetes_namespace, body=job_launcher)
        self._stream_pod_logs()

    @error_wrapper
    def _delete_k8s_job(self, namespace: str, job_name: str, wait: bool = True, timeout: int = 60):
        try:
            response = self._batch_v1.delete_namespaced_job(
                name=job_name,
                namespace=namespace,
                body=client.V1DeleteOptions(propagation_policy='Foreground')
            )
            print(f"🗑️ Deletion requested for Job '{job_name}' in namespace '{namespace}'")

            if wait:
                for i in range(timeout):
                    try:
                        self._batch_v1.read_namespaced_job(job_name, namespace)
                        print(f"⏳ Waiting for Job '{job_name}' to be deleted... ({i+1}s)")
                        time.sleep(1)
                    except ApiException as e:
                        if e.status == 404:
                            print(f"✅ Job '{job_name}' fully deleted.")
                            return True
                        else:
                            raise
                raise TimeoutError(f"❌ Timed out: Job '{job_name}' was not deleted within {timeout} seconds.")

            return response
        except ApiException as e:
            if e.status == 404:
                print(f"ℹ️ Job '{job_name}' not found → Ready to create new.")
                return False
            else:
                raise
    
    @error_wrapper
    def kuberenetes_config(self,config_file:dict,ssl_ignore:bool=False):
        if config_file:
            config.load_kube_config(config_file=config_file["config_file"])
        else:
            config.load_kube_config()
        conf = Configuration.get_default_copy()
        conf.verify_ssl = ssl_ignore or False
        Configuration.set_default(conf)

        # API clients
        self._core_v1 = client.CoreV1Api()
        self._batch_v1 = client.BatchV1Api()
        self._storage_v1 = client.StorageV1Api()
    
    @error_wrapper
    def _gpu_resources(self,gpus:int=None):
        if gpus is not None:
            return {
                "requests": {"nvidia.com/gpu": str(gpus)},
                "limits": {"nvidia.com/gpu": str(gpus)},
            }
        return None
    
    def _path_finder(self,locate):
        import inspect
        caller_file = inspect.stack()[-1].filename
        caller_path = Path(caller_file).resolve()
        if locate == "caller_path":
            return caller_path
        elif locate == "caller_dir":
            return caller_path.parent.resolve().as_posix()
    
    @error_wrapper
    def _stream_pod_logs(self):
        try:
            pod_name = self._wait_for_pod()
        except TimeoutError as e:
            print(str(e))
            return
        pods = self._core_v1.list_namespaced_pod(self._kubernetes_namespace, label_selector=f"job-name={self._Pyssion_namespace.job_name}")
        pod_name = pods.items[0].metadata.name

        w = watch.Watch()
        for line in w.stream(
            self._core_v1.read_namespaced_pod_log,
            name=pod_name,
            namespace=self._kubernetes_namespace,
            follow=True,
            _preload_content=False,
        ):
            print(line.strip() if isinstance(line, str) else line.decode("utf-8").strip())
    
    def _wait_for_pod(self, timeout: int = 60) -> str:
        """
        Wait until job pod is created and ready to stream logs.
        Returns:
            pod_name (str)
        """
        for _ in range(timeout):
            pods = self._core_v1.list_namespaced_pod(
                namespace=self._kubernetes_namespace,
                label_selector=f"job-name={self._Pyssion_namespace.job_name}"
            )

            if pods.items:
                pod = pods.items[0]
                phase = pod.status.phase
                if phase in ["Running", "Succeeded", "Failed"]:
                    return pod.metadata.name
                elif phase == "Pending" and pod.status.container_statuses:
                    state = pod.status.container_statuses[0].state
                    if state.waiting:
                        reason = state.waiting.reason
                        print(f"⏳ Pod is pending... Reason: {reason}")
                    else:
                        print("⏳ Pod is pending... No detailed reason available.")
                else:
                    print(f"⏳ Pod status: {phase}")
            else:
                print("⏳ Waiting for pod to appear...")

            time.sleep(1)

        raise TimeoutError("❌ Pod did not appear within timeout.")