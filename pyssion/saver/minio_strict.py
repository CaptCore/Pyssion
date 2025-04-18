import os
from pathlib import Path
import hashlib
from minio import Minio

# —— settings ——
endpoint = os.getenv("PYSSION_MINIO_ENDPOINT")
access_key = os.getenv("PYSSION_MINIO_ACCESSKEY")
secret_key = os.getenv("PYSSION_MINIO_SECRETKEY")
bucket_name = os.getenv("PYSSION_MINIO_BUCKET")
prefix = os.getenv("PYSSION_MINIO_PREFIX","")
download_root = Path("/app/code")

client = Minio(
    endpoint,
    access_key=access_key,
    secret_key=secret_key,
    secure=False
)

# local md5 hash
def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# MinIO object search
objects = client.list_objects(bucket_name, prefix=prefix, recursive=True)
for obj in objects:
#address parse
    rel_path = obj.object_name.replace((str(prefix)+"/"), "")
    dst = download_root / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)

#get meta data 
    stat = client.stat_object(bucket_name, obj.object_name)
    remote_size = stat.size
#get minio ETag
    remote_etag = stat.etag.strip('"')

# if local has that file, compare MD5(ETag)
    if dst.exists():
        local_size = dst.stat().st_size
        local_etag = file_md5(dst)
        if local_size == remote_size and local_etag == remote_etag:
            print(f"✔️ Skipped (identical): {dst}")
            continue

# If not same, Download
    client.fget_object(bucket_name, obj.object_name, str(dst))
    print(f"📥 Downloaded: {dst}")