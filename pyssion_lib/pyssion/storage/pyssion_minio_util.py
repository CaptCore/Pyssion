from minio.error import S3Error
from pathlib import Path
from pyssion.saver.pyssion_ignore import load_ignore_patterns,should_ignore,get_local_etag
import os


def minio_uploader(directory_path: str, client, bucket: str, prefix: str = ""):
    """
    - directory_path: target upload workload directory path
    - client: MinIO Python client Instance
    - bucket: target bucket name
    - prefix: (prefix)
    """
    base = Path(directory_path)
    ignore_patterns = load_ignore_patterns(base)

    for root, dirs, files in os.walk(base):
        rel_root = Path(root).relative_to(base)

        # 1) ignore
        for dirname in dirs[:]:
            rel_dir = rel_root / dirname
            if should_ignore(rel_dir, ignore_patterns):
                print(f"📂 skipped directory: {rel_dir.as_posix()}")
                dirs.remove(dirname)

        # 2) each file
        for filename in files:
            rel_file = rel_root / filename
            if should_ignore(rel_file, ignore_patterns):
                print(f"📤 skipped file: {rel_file.as_posix()}")
                continue

            object_name = f"{prefix}/{rel_file.as_posix()}".lstrip("/")
            local_path = Path(root) / filename
            local_etag = get_local_etag(str(local_path))

            # 3) minio eTag 
            try:
                stat = client.stat_object(bucket, object_name)
                remote_etag = stat.etag.strip('"')  # MinIO eTag
                if local_etag == remote_etag:
                    print(f"↩️ Skipping unchanged: {object_name}")
                    continue
            except S3Error as e:
                # No object -> continue, Other Error -> Raise E
                if e.code != "NoSuchKey":
                    raise

            # 4) Change or New -> upload
            client.fput_object(bucket, object_name, str(local_path))
            print(f"📤 Upload: {object_name}")
