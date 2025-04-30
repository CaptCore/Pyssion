import os
from minio import Minio
from pathlib import Path
import subprocess

endpoint = os.environ["MINIO_ENDPOINT"]
access_key = os.environ["MINIO_ACCESS"]
secret_key = os.environ["MINIO_SECRET"]
bucket = os.environ["MINIO_BUCKET"]
prefix = os.environ["MINIO_PREFIX"]
entrypoint = os.environ["ENTRYPOINT_FILE"]

client = Minio(endpoint, access_key, secret_key, secure=False)
objects = client.list_objects(bucket, prefix=prefix, recursive=True)

Path("/app/code").mkdir(parents=True, exist_ok=True)

for obj in objects:
    filename = obj.object_name.replace(f"{prefix}/", "")
    save_path = os.path.join("/app/code", filename)
    Path(os.path.dirname(save_path)).mkdir(parents=True, exist_ok=True)
    client.fget_object(bucket, obj.object_name, save_path)

subprocess.run(["python", f"/app/code/{entrypoint}"])
