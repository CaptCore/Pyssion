from pyssion.core import Pyssion

if __name__ == "__main__":
    p = Pyssion(
        minio_config={
            "endpoint": "172.20.1.17:9000",  # MinIO 도커 컨테이너 주소
            "access_key": "minio",
            "secret_key": "minio123",
            "bucket": "fussion",
        },
        k8s_config={"namespace": "default", "job_name": "fussion-job-test"},
    )
    p.run()

    print("test done.")
