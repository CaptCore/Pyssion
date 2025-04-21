import os
import hashlib
from pathlib import Path
from minio import Minio

# —— 설정 ——
endpoint = os.getenv("PYSSION_MINIO_ENDPOINT")
access_key = os.getenv("PYSSION_MINIO_ACCESSKEY")
secret_key = os.getenv("PYSSION_MINIO_SECRETKEY")
bucket = os.getenv("PYSSION_MINIO_BUCKET")
prefix = os.getenv("PYSSION_MINIO_PREFIX", "")
download_root = Path("/app/code")

# MinIO 클라이언트 초기화
client = Minio(
    endpoint,
    access_key=access_key,
    secret_key=secret_key,
    secure=False
)

def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# 객체 목록 순회
for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
    rel_path = obj.object_name.replace(f"{prefix}/", "")
    dst = download_root / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)

    # 원격 메타데이터 조회
    stat = client.stat_object(bucket, obj.object_name)
    remote_size = stat.size
    remote_etag = stat.etag.strip('"')

    # 로컬 파일이 존재하면 비교
    if dst.exists():
        local_size = dst.stat().st_size
        local_etag = file_md5(dst)
        if local_size == remote_size and local_etag == remote_etag:
            continue

    # 다운로드
    client.fget_object(bucket, obj.object_name, str(dst))
    print(f"📥 다운로드 완료: {rel_path}")