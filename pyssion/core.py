# pyssion/core.py
import io
import zipfile
import base64
import json
from pathlib import Path
from kubernetes import client, config
from kubernetes.client import Configuration

from pyssion.core_util.path_util import generate_random_string
from pyssion.saver.pyssion_ignore import load_ignore_patterns, should_ignore
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
        self._unique_job_name = self._generate_unique_job_name()
        self._minio_config = minio_config or None
        self._k8s_config = k8s_config or None
        self._namespace = self._k8s_config.get("namespace", "default")
        self._entrypoint_file = entrypoint_file or None
        self._req_file = req_file or None
        self._gpus = self._gpu_resources(gpus) or None
        self._fast_use = fast_use or None

    @error_wrapper
    def run(self):
        print("✅ pyssion Fission!")
        self.kuberenetes_config(self._k8s_config)
        print("✅ Get Pyssion Config Data!")
        print(f"Pyssion job name : {self._unique_job_name}")
        print("✅ Create PVC")
        self._create_configmap_with_zipped_code()
        job_launcher = KubernetesJobCreator(
            image="python",
            job_name=self._unique_job_name,
            namespace=self._namespace,
            resource=self._gpus,
            req_file=self._req_file,
            entrypoint_file=self._entrypoint_file
        ).build_job_spec()
        self._batch_v1.create_namespaced_job(namespace=self._namespace, body=job_launcher)
    
    @error_wrapper
    def _create_configmap_with_zipped_code(self):
        caller_dir = Path(self._path_finder("caller_dir"))
        ignore_patterns = load_ignore_patterns(caller_dir)

        # 압축
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for path in caller_dir.rglob("*"):
                if path.is_file() and path.stat().st_size < 1_000_000:
                    rel_path = path.relative_to(caller_dir)
                    if should_ignore(rel_path, ignore_patterns):
                        continue
                    zipf.write(path, arcname=str(rel_path))

        zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode("utf-8")

        configmap = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(name=self._unique_job_name),
            data={"code.zip.b64": zip_base64}
        )

        try:
            self._core_v1.create_namespaced_config_map(
                namespace=self._namespace,
                body=configmap
            )
            print(f"📦 ConfigMap '{self._unique_job_name}' created (zipped)")
        except client.exceptions.ApiException as e:
            if e.status == 409:
                print(f"🔁 ConfigMap '{self._unique_job_name}' already exists, replacing")
                self._core_v1.replace_namespaced_config_map(
                    name=self._unique_job_name,
                    namespace=self._namespace,
                    body=configmap
                )
            else:
                raise
            
    @error_wrapper
    def _generate_unique_job_name(self) -> str:
        project_dir = self._path_finder("caller_dir")
        cache_file = Path(project_dir) / ".pyssioncache"

        if cache_file.exists():
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            prefix = data.get("prefix", generate_random_string())
        else:
            prefix = generate_random_string()
            cache_file.write_text(json.dumps({"prefix": prefix}), encoding="utf-8")

        return f"pyssion-job-{prefix}"
    
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
    
    @error_wrapper
    def minio_setup(self,minio_config:dict):
        from pyssion.saver.minio_client import MinioUploader
        import json
        import uuid
        
        caller_path = self._path_finder("caller_path")
        project_dir = Path(self._path_finder("caller_dir"))
        cache_file = project_dir / ".pyssioncache"
        if cache_file.exists():
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            unique_id = data.get("prefix")
        else:
            unique_id = str(uuid.uuid4())[:8]
            cache_file.write_text(json.dumps({"prefix": unique_id}), encoding="utf-8")
        modified_path = self._comment_out_pyssion_block(caller_path)
        uploader = MinioUploader(minio_config)
        uploader.upload_all(project_dir, prefix=unique_id)
        uploader.upload_single(
            modified_path,
            prefix=unique_id,
            object_name=f"{unique_id}/{caller_path.name}"
        )
        return self._decode_k8s_config(unique_id=unique_id)
    
    def _path_finder(self,locate):
        import inspect
        caller_file = inspect.stack()[-1].filename
        caller_path = Path(caller_file).resolve()
        if locate == "caller_path":
            return caller_path
        elif locate == "caller_dir":
            return caller_path.parent.resolve().as_posix()