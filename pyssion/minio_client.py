from minio import Minio
from pathlib import Path

class MinioUploader:
    def __init__(self, endpoint, access_key, secret_key, bucket):
        self.bucket = bucket
        self.client = Minio(endpoint, access_key, secret_key, secure=False)
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def upload_directory(self, directory_path, prefix=""):
        directory = Path(directory_path)
        for path in directory.rglob("*"):
            if path.is_file():
                object_name = f"{prefix}/{path.relative_to(directory)}"
                self.client.fput_object(self.bucket, object_name, str(path))
                print(f"📤 업로드: {object_name}")

    def upload_file(self, filepath, prefix, object_name=None):
        if object_name is None:
            object_name = f"{prefix}/{filepath.name}"
        self.client.fput_object(self.bucket, object_name, str(filepath))

