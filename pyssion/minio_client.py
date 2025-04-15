from minio import Minio
import fnmatch
import os
from pathlib import Path
from pyssion.pyssion_ignore import upload_directory

class MinioUploader:
    def __init__(self, endpoint, access_key, secret_key, bucket):
        self.bucket = bucket
        self.client = Minio(endpoint, access_key, secret_key, secure=False)
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def upload_directory(self, directory_path, prefix=""):
        upload_directory(directory_path, self.client, self.bucket, prefix)

    def upload_file(self, filepath, prefix, object_name=None):
        if object_name is None:
            object_name = f"{prefix}/{filepath.name}"
        self.client.fput_object(self.bucket, object_name, str(filepath))