from kubernetes import client, config
from pathlib import Path
import hashlib

def generate_kaniko_build_job_spec(job_name: str, context_bucket: str, dockerfile_path: str, image_dest: str,config_file=None, namespace: str = "default") -> client.V1Job:
    if config_file == None:
        config.load_kube_config()
        print("📦 Loaded kubeconfig from local file")
    else:
        config.load_kube_config(config_file=config_file)
        print("📦 Loaded kubeconfig from local file")
    
    return client.V1Job(
        metadata=client.V1ObjectMeta(name=f"kaniko-build-{job_name}"),
        spec=client.V1JobSpec(
            backoff_limit=0,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"job": f"kaniko-build-{job_name}"}),
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    service_account_name="pyssion-kaniko",
                    containers=[
                        client.V1Container(
                            name="kaniko",
                            image="gcr.io/kaniko-project/executor:latest",
                            args=[
                                f"--dockerfile={dockerfile_path}",
                                f"--context=s3://{context_bucket}/{job_name}/",
                                f"--destination={image_dest}",
                                "--insecure", "--insecure-pull", "--insecure-registry"
                            ],
                            env=[
                                client.V1EnvVar(name="AWS_ACCESS_KEY_ID", value_from=client.V1EnvVarSource(
                                    secret_key_ref=client.V1SecretKeySelector(name="minio-secret", key="accessKey")
                                )),
                                client.V1EnvVar(name="AWS_SECRET_ACCESS_KEY", value_from=client.V1EnvVarSource(
                                    secret_key_ref=client.V1SecretKeySelector(name="minio-secret", key="secretKey")
                                )),
                                client.V1EnvVar(name="S3_ENDPOINT", value="http://minio.default.svc.cluster.local:9000"),
                                client.V1EnvVar(name="S3_FORCE_PATH_STYLE", value="true"),
                                client.V1EnvVar(name="SSL_CERT_DIR", value="/kaniko/ssl")
                            ]
                        )
                    ]
                )
            )
        )
    )

def launch_kaniko_build_job(job_spec: client.V1Job,config_file=None, namespace: str = "default"):
    if config_file == None:
        config.load_kube_config()
        print("📦 Loaded kubeconfig from local file")
    else:
        config.load_kube_config(config_file=config_file)
        print("📦 Loaded kubeconfig from local file")

    batch_api = client.BatchV1Api()
    try:
        batch_api.create_namespaced_job(namespace=namespace, body=job_spec)
        print(f"🚀 Kaniko build job '{job_spec.metadata.name}' launched.")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            print(f"⚠️ Job '{job_spec.metadata.name}' already exists.")
        else:
            raise