# pyssion/k8s_client.py
from kubernetes import client, config, watch
from kubernetes.client import Configuration
import time

def wait_for_job_completion(namespace, job_name):
    batch = client.BatchV1Api()
    while True:
        job = batch.read_namespaced_job_status(job_name, namespace)
        status = job.status
        if status.succeeded:
            print("✅ Job succeeded.")
            return "Complete"
        elif status.failed:
            print("❌ Job failed.")
            return "Failed"
        time.sleep(1)

def print_job_logs(namespace, job_name):
    core = client.CoreV1Api()
    pod_list = core.list_namespaced_pod(namespace, label_selector=f"job-name={job_name}")
    pod_name = pod_list.items[0].metadata.name
    logs = core.read_namespaced_pod_log(pod_name, namespace)
    print(f"\n📦 print log (Pod: {pod_name}):\n{'-' * 30}\n{logs}\n{'-' * 30}")

class KubernetesJobLauncher:
    def __init__(self, image, job_name, namespace, minio_env, entrypoint_file, config_file=None):
        self.image = image
        self.job_name = job_name
        self.namespace = namespace
        self.minio_env = minio_env
        self.entrypoint_file = entrypoint_file
        self.config_file = config_file if config_file is not None else None

    def launch(self):
        if self.config_file == None:
            config.load_kube_config()
        else:
            config.load_kube_config(config_file=self.config_file)
        
        c = Configuration.get_default_copy()
        c.verify_ssl = False
        Configuration.set_default(c)

        batch_v1 = client.BatchV1Api()
        env_list = [client.V1EnvVar(name=k, value=v) for k, v in self.minio_env.items()]

        command_script = f'''
        pip install minio && \
        python -c """
import os, subprocess
from pathlib import Path
from minio import Minio

client = Minio(
    '{self.minio_env['MINIO_ENDPOINT']}',
    '{self.minio_env['MINIO_ACCESS']}',
    '{self.minio_env['MINIO_SECRET']}',
    secure=False
)

objs = client.list_objects(
    '{self.minio_env['MINIO_BUCKET']}',
    prefix='{self.minio_env['MINIO_PREFIX']}',
    recursive=True
)

Path('/app/code').mkdir(parents=True, exist_ok=True)

for obj in objs:
    rel = obj.object_name.replace('{self.minio_env['MINIO_PREFIX']}/', '')
    dst = os.path.join('/app/code', rel)
    Path(os.path.dirname(dst)).mkdir(parents=True, exist_ok=True)
    client.fget_object('{self.minio_env['MINIO_BUCKET']}', obj.object_name, dst)

subprocess.run(['python3', '/app/code/{self.entrypoint_file}'], check=True)
"""
        '''.strip()

        container = client.V1Container(
            name="runner",
            image=self.image,
            command=["sh", "-c"],
            args=[command_script],
            env=env_list
        )

        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"job-name": self.job_name}),
            spec=client.V1PodSpec(restart_policy="Never", containers=[container])
        )

        job_spec = client.V1JobSpec(template=template, backoff_limit=0)
        job = client.V1Job(
            metadata=client.V1ObjectMeta(name=self.job_name),
            spec=job_spec
        )

        batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
        print(f"🚀 kubernetes Job launch: {self.job_name}")
        status = wait_for_job_completion(self.namespace, self.job_name)
        print(f"Job's status : {status}")
        print_job_logs(self.namespace, self.job_name)