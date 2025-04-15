from minio import Minio
import fnmatch
from pathlib import Path

class MinioUploader:
    def __init__(self, endpoint, access_key, secret_key, bucket):
        self.bucket = bucket
        self.client = Minio(endpoint, access_key, secret_key, secure=False)
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def upload_directory(self, directory_path, prefix=""):
        directory = Path(directory_path)
        
        ignore_file = directory / '.pyssionignore'
        ignore_patterns = []
        if ignore_file.exists():
            with ignore_file.open() as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ignore_patterns.append(line)

        for path in directory.rglob("*"):
            if path.is_file():
                relative_path = str(path.relative_to(directory))
                skip = False
                for pattern in ignore_patterns:
                    if fnmatch.fnmatch(relative_path, pattern):
                        skip = True
                        print(f"📤 스킵됨 (패턴 '{pattern}' 매칭): {relative_path}")
                        break
                if skip:
                    continue

                object_name = f"{prefix}/{relative_path}"
                self.client.fput_object(self.bucket, object_name, str(path))
                print(f"📤 업로드: {object_name}")

    def upload_file(self, filepath, prefix, object_name=None):
        if object_name is None:
            object_name = f"{prefix}/{filepath.name}"
        self.client.fput_object(self.bucket, object_name, str(filepath))