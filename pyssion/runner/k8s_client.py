# pyssion/k8s_client.py
from kubernetes import client, config
from kubernetes.client import Configuration
from pyssion.runner.k8s_container import pyssion_container, timer, logviewer
from pyssion.handler.error_handler import error_wrapper
from pyssion.handler.handler_main import origin_pyssion

#main K8s Job Builder
class KubernetesJobLauncher(origin_pyssion):
    def __init__(self, image, job_name, namespace, minio_env, resource, req_file=None, config_file=None):
        self.name = "Pyssion Kubernetes client"
        self.image = image
        self.job_name = job_name
        self.namespace = namespace
        self.minio_env = minio_env
        self.config_file = config_file if config_file is not None else None
        self.resource = resource
        self.req_file = f"/app/code/{req_file}" if req_file is not None else None

    @error_wrapper
    def launch(self,warn_ignore,ssl_ignore=False):
        #check config_file
        if self.config_file == None:
            config.load_kube_config()
        else:
            config.load_kube_config(config_file=self.config_file)
        
        #config ready
        c = Configuration.get_default_copy()
        if ssl_ignore == True:
            c.verify_ssl = False
        Configuration.set_default(c)

        batch_v1 = client.BatchV1Api()
        env_list = [client.V1EnvVar(name=k, value=v) for k, v in self.minio_env.items()]
        command_script = pyssion_container( self.minio_env, req_file=self.req_file )

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
        status = timer(self.namespace, self.job_name, warn_ignore)
        
        logviewer(self.namespace, self.job_name)
        print(f"Job's status : {status}")