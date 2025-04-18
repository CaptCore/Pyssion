# pyssion/core.py
import uuid
import inspect
import tempfile
from pathlib import Path
from pyssion.saver.minio_client import MinioUploader
from pyssion.runner.k8s_client import KubernetesJobLauncher
from pyssion.core_util.util import generate_random_string
from pyssion.handler.error_handler import error_wrapper
from pyssion.handler.handler_main import origin_pyssion
from kubernetes import client

class Pyssion(origin_pyssion):
    def __init__(self, minio_config, k8s_config, entrypoint_file=None,req_file=None, gpus=None, cache=None):
        self.name = "Pyssion Core"
        self.minio_config = minio_config
        self.k8s_config = k8s_config
        self.entrypoint_file = entrypoint_file if entrypoint_file is not None else None
        if gpus != None:
            #if gpus on, self.k8s_config will be changed
            self._instance_check(gpus)
        self.req_file = req_file if req_file is not None else None
        if cache != None:
            print(f"cache status : {cache}")
            self._cache_check()
        

    @error_wrapper
    def run(self,warn_ignore=None,ssl_ignore=None):
        print("✅ pyssion Fission!")
        #minio work ready & launch
        image,namespace,job_name,config_file,resource,minio_env = self._minio_work()
        #Kubernetes work ready
        job_launcher = KubernetesJobLauncher(
            image=image,
            job_name=job_name,
            namespace=namespace,
            config_file=config_file,
            resource=resource,
            req_file=self.req_file,
            minio_env=minio_env
        )
        #Kubernetes work launch
        job_launcher.launch(warn_ignore,ssl_ignore)

    @error_wrapper
    def _comment_out_pyssion_block(self, filepath: Path) -> Path:
        with open(filepath, "r") as f:
            lines = f.readlines()

        modified_lines = []
        inside_pyssion_block = False
        for line in lines:
            if "from pyssion.core import Pyssion" in line:
                modified_lines.append("# " + line)
            elif "Pyssion(" in line:
                inside_pyssion_block = True
                modified_lines.append("# " + line)
            elif inside_pyssion_block:
                modified_lines.append("# " + line)
                if line.strip().endswith(")"):
                    inside_pyssion_block = False
            elif "p.run()" in line:
                modified_lines.append("# " + line)
            else:
                modified_lines.append(line)

        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py")
        temp_file.writelines(modified_lines)
        temp_file.close()

        return Path(temp_file.name)
    
    @error_wrapper
    def _minio_work(self):
        #get caller's path for draft all files
        caller_file = inspect.stack()[-1].filename
        caller_path = Path(caller_file).resolve()
        project_dir = caller_path.parent.resolve().as_posix()
        #check entry_point
        
        entrypoint_file = self.entrypoint_file if self.entrypoint_file is not None else caller_path.name
        unique_id = str(uuid.uuid4())[:8]

        modified_path = self._comment_out_pyssion_block(caller_path)

        uploader = MinioUploader(**self.minio_config)
        uploader.upload_all(project_dir, prefix=unique_id)
        uploader.upload_single(modified_path, prefix=unique_id, object_name=f"{unique_id}/{caller_path.name}")

        image,namespace,job_name,config_file,resource = self._decode_k8s_config()

        minio_env={
                "MINIO_ENDPOINT": self.minio_config["endpoint"],
                "MINIO_BUCKET": self.minio_config["bucket"],
                "MINIO_ACCESS": self.minio_config["access_key"],
                "MINIO_SECRET": self.minio_config["secret_key"],
                "MINIO_PREFIX": unique_id,
                "ENTRYPOINT_FILE": entrypoint_file
            }

        return image, namespace, job_name, config_file, resource, minio_env

    @error_wrapper
    def _decode_k8s_config(self):
        if "image" in self.k8s_config:
            image = self.k8s_config["image"]
        else:
             image = "python"
        if "namespace" in self.k8s_config:
            namespace = self.k8s_config["namespace"]
        else:
            namespace = "default"
        if "job_name" in self.k8s_config:
            job_name = self.k8s_config["job_name"]
        else:
            job_name = f"pyssion-job-{generate_random_string()}"
        if  "config_file" in self.k8s_config:
            config_file = self.k8s_config["config_file"]
        else:
            config_file = None
        if "resources" in self.k8s_config:
            resource = client.V1ResourceRequirements(**self.k8s_config["resources"])
        else:
            resource = None
        
        return image,namespace,job_name,config_file,resource
    
    @error_wrapper
    def _instance_check(self,gpus):
        if gpus is not None:
            if "resources" not in self.k8s_config:
                self.k8s_config["resources"] = {"requests": {}, "limits": {}}

            self.k8s_config["resources"]["requests"]["nvidia.com/gpu"] = str(gpus)
            self.k8s_config["resources"]["limits"]["nvidia.com/gpu"] = str(gpus)
    
    @error_wrapper
    def _cache_check(self):
        caller_file = inspect.stack()[-1].filename
        caller_path = Path(caller_file).resolve()
        print(f"path find: {caller_path}")
        raise SyntaxError