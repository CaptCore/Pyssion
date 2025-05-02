import random
import string
import os

import json
import inspect
from pathlib import Path

# Core Function Archive :: Later will be activate
# import io
# import zipfile
# import base64
# from kubernetes import client

# from pyssion.saver.pyssion_ignore import load_ignore_patterns,should_ignore

def generate_random_string():
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(6))

def generate_pyssion_cache_file(cache_dir:str):
    cachename = os.path.join(generate_random_string(),".pyssioncache")
    cache_full_path = os.path.join(cache_dir,cachename)
    return cache_full_path

class Pyssion_Namespace:
    def __init__(self):
        self.pyssion_unique_name = self._generate_unique_job_name()
        self.job_name = f"pyssion-job-{self.pyssion_unique_name}"
        self.volume_name = f"pyssion-volume-{self.pyssion_unique_name}"
        self.pvc_name = f"pyssion-pvc-{self.pyssion_unique_name}"
    
    def _generate_unique_job_name(self) -> str:
        self.project_dir = self._path_finder("caller_dir")
        cache_file = Path(self.project_dir) / ".pyssioncache"

        if cache_file.exists():
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            prefix = data.get("prefix", generate_random_string())
        else:
            prefix = generate_random_string()
            cache_file.write_text(json.dumps({"prefix": prefix}), encoding="utf-8")

        return prefix
    
    def _path_finder(self,locate):
        caller_file = inspect.stack()[-1].filename
        caller_path = Path(caller_file).resolve()
        if locate == "caller_path":
            return caller_path
        elif locate == "caller_dir":
            return caller_path.parent.resolve().as_posix()
    
#Core Function Archieving

# def _create_configmap_with_zipped_code(self):
#     caller_dir = Path(self._path_finder("caller_dir"))
#     ignore_patterns = load_ignore_patterns(caller_dir)

#     # 압축
#     zip_buffer = io.BytesIO()
#     with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
#         for path in caller_dir.rglob("*"):
#             if path.is_file() and path.stat().st_size < 1_000_000:
#                 rel_path = path.relative_to(caller_dir)
#                 if should_ignore(rel_path, ignore_patterns):
#                     continue
#                 zipf.write(path, arcname=str(rel_path))

#     zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode("utf-8")

#     configmap = client.V1ConfigMap(
#         metadata=client.V1ObjectMeta(name=self._unique_job_name),
#         data={"code.zip.b64": zip_base64}
#     )

#     try:
#         self._core_v1.create_namespaced_config_map(
#             namespace=self._kubernetes_namespace,
#             body=configmap
#         )
#         print(f"📦 ConfigMap '{self._unique_job_name}' created (zipped)")
#     except client.exceptions.ApiException as e:
#         if e.status == 409:
#             print(f"🔁 ConfigMap '{self._unique_job_name}' already exists, replacing")
#             self._core_v1.replace_namespaced_config_map(
#                 name=self._unique_job_name,
#                 namespace=self._kubernetes_namespace,
#                 body=configmap
#             )
#         else:
#             raise