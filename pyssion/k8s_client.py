# pyssion/k8s_client.py
from kubernetes import client, config, watch
from kubernetes.client import Configuration
from pyssion.script_builder import generate_command_script
import time

def wait_for_job_completion(namespace, job_name,ignore=None):
    if ignore != None:
        from urllib3.exceptions import InsecureRequestWarning
        from urllib3 import disable_warnings
        disable_warnings(InsecureRequestWarning)
    batch = client.BatchV1Api()
    counter = 0
    while True:
        counter += 1
        job = batch.read_namespaced_job_status(job_name, namespace)
        status = job.status
        if status.succeeded:
            print("✅ Job succeeded.")
            return True
        elif status.failed:
            print("❌ Job failed.")
            return False
        else:
            print(f"🕐 Still Run. {counter} second(s) have passed.")
        time.sleep(1)

def print_job_logs(namespace, job_name):
    core = client.CoreV1Api()
    pod_list = core.list_namespaced_pod(namespace, label_selector=f"job-name={job_name}")
    pod_name = pod_list.items[0].metadata.name
    logs = core.read_namespaced_pod_log(pod_name, namespace)
    print(f"\n📦 print log (Pod: {pod_name}):\n{'-' * 30}\n{logs}\n{'-' * 30}")

class KubernetesJobLauncher:
    def __init__(self, image, job_name, namespace, minio_env, resource, entrypoint_file, req_file=None, config_file=None):
        self.image = image
        self.job_name = job_name
        self.namespace = namespace
        self.minio_env = minio_env
        self.entrypoint_file = entrypoint_file
        self.config_file = config_file if config_file is not None else None
        self.resource = resource
        self.req_file = f"/app/code/{req_file}" if req_file is not None else None

    def launch(self,ignore):
        if self.config_file == None:
            config.load_kube_config()
        else:
            config.load_kube_config(config_file=self.config_file)
        
        c = Configuration.get_default_copy()
        c.verify_ssl = False
        Configuration.set_default(c)

        batch_v1 = client.BatchV1Api()
        env_list = [client.V1EnvVar(name=k, value=v) for k, v in self.minio_env.items()]
        command_script = generate_command_script( self.minio_env, entrypoint_file=self.entrypoint_file, req_file=self.req_file )

        container = client.V1Container(
            name="runner",
            image=self.image,
            command=["sh", "-c"],
            args=[command_script],
            env=env_list,
            resources=self.resource
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
        status = wait_for_job_completion(self.namespace, self.job_name, ignore)
        
        print_job_logs(self.namespace, self.job_name)
        print(f"Job's status : {status}")