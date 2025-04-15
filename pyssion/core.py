# pyssion/core.py
import os
import uuid
import inspect
import tempfile
from pathlib import Path
from pyssion.minio_client import MinioUploader
from pyssion.k8s_client import KubernetesJobLauncher
from pyssion.util import generate_random_string

class Pyssion:
    def __init__(self, minio_config, k8s_config,entrypoint_file=None):
        self.minio_config = minio_config
        self.k8s_config = k8s_config
        self.entrypoint_file = entrypoint_file if entrypoint_file is not None else None

    def run(self):
        #get caller's path for draft all files
        caller_file = inspect.stack()[-1].filename
        caller_path = Path(caller_file).resolve()
        project_dir = caller_path.parent.resolve().as_posix()
        #check entry_point
        
        entrypoint_file = self.entrypoint_file if self.entrypoint_file is not None else caller_path.name
        unique_id = str(uuid.uuid4())[:8]

        modified_path = self._comment_out_pyssion_block(caller_path)

        uploader = MinioUploader(**self.minio_config)
        uploader.upload_directory(project_dir, prefix=unique_id)
        uploader.upload_file(modified_path, prefix=unique_id, object_name=f"{unique_id}/{entrypoint_file}")

        image,namespace,job_name,config_file = self._decode_k8s_config()

        job_launcher = KubernetesJobLauncher(
            image=image,
            job_name=job_name,
            namespace=namespace,
            config_file=config_file,
            entrypoint_file=entrypoint_file,
            minio_env={
                "MINIO_ENDPOINT": self.minio_config["endpoint"],
                "MINIO_BUCKET": self.minio_config["bucket"],
                "MINIO_ACCESS": self.minio_config["access_key"],
                "MINIO_SECRET": self.minio_config["secret_key"],
                "MINIO_PREFIX": unique_id,
                "ENTRYPOINT_FILE": entrypoint_file
            }
        )
        job_launcher.launch()
        print("✅ pyssion 작업이 시작되었습니다.")

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
        
        return image,namespace,job_name,config_file