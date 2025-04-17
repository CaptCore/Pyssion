from minio import Minio
from pyssion.saver.pyssion_ignore import minio_uploader
from pyssion.handler.error_handler import error_wrapper
from pyssion.handler.handler_main import origin_pyssion

class MinioUploader(origin_pyssion):
    def __init__(self, endpoint, access_key, secret_key, bucket):
        self.name = "Pyssion Minio Uploader"
        self.bucket = bucket
        self.client = Minio(endpoint, access_key, secret_key, secure=False)
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    @error_wrapper
    def upload_all(self, directory_path, prefix=""):
        minio_uploader(directory_path, self.client, self.bucket, prefix)

    @error_wrapper
    def upload_single(self, filepath, prefix, object_name=None):
        if object_name is None:
            object_name = f"{prefix}/{filepath.name}"
        self.client.fput_object(self.bucket, object_name, str(filepath))