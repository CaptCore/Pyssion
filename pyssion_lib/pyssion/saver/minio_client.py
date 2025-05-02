import fnmatch
import hashlib
from pathlib import Path
from minio import Minio

class MinioUploader:
    def __init__(self, minio_config: dict):
        self.client = Minio(
            minio_config["MINIO_ENDPOINT"],
            access_key=minio_config["MINIO_ACCESS"],
            secret_key=minio_config["MINIO_SECRET"],
            secure=False
        )
        self.bucket = minio_config["MINIO_BUCKET"]
        self.prefix = minio_config["MINIO_PREFIX"]
        self.ignore_patterns = []

    def upload_project(self, project_dir: Path):
        project_dir = Path(project_dir)
        self._load_ignore_patterns(project_dir)

        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

        for file in project_dir.rglob("*"):
            if file.is_file():
                rel_path = file.relative_to(project_dir)
                if self._should_ignore(rel_path):
                    print(f"🚫 Ignored: {rel_path}")
                    continue

                remote_path = f"{self.prefix}/{rel_path.as_posix()}"
                print(f"⬆️ Uploading: {rel_path} → {remote_path}")
                self.client.fput_object(self.bucket, remote_path, str(file))

    def _load_ignore_patterns(self, directory: Path):
        ignore_file = directory / ".pyssionignore"
        if ignore_file.exists():
            with ignore_file.open("r", encoding="utf-8") as f:
                self.ignore_patterns = [
                    line.strip() for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]

    def _should_ignore(self, relative_path: Path) -> bool:
        rel_str = relative_path.as_posix()
        for pattern in self.ignore_patterns:
            if pattern.endswith("/"):
                if rel_str == pattern.rstrip("/") or rel_str.startswith(pattern):
                    return True
            elif fnmatch.fnmatch(rel_str, pattern):
                return True
        return False

    def get_local_etag(self, file_path: str) -> str:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
