import time
from kubernetes import client
import docker
from docker.errors import BuildError

from pyssion.core_util.path_util import generate_random_string
        
#Container Runner
def pyssion_job_container(minio_env: dict, minio_mirror:bool = False, pyssion_configmap_name:str = None, image="python", req_file: str = None, resources: client.V1ResourceRequirements = None):
    """
    - minio_env: {
    #     "MINIO_ENDPOINT": 'minio_env["MINIO_ENDPOINT"]',
    #     "MINIO_ACCESS": "minio_env["MINIO_ACCESS"]",
    #     "MINIO_SECRET": "minio_env["MINIO_SECRET"]",
    #     "MINIO_BUCKET": "minio_env["MINIO_BUCKET"]",
    #     "MINIO_PREFIX": "minio_env["MINIO_PREFIX"]",
    #     "ENTRYPOINT_FILE": minio_env["ENTRYPOINT_FILE"]
    # }
    - req_file: req_file
    """
    if pyssion_configmap_name == None:
        pyssion_configmap_name = "pyssion-cache-script"

    # 1) EnvVars
    env_vars = container_env_var_builder(minio_env)
    cmd = command_builder(minio_env,minio_mirror,req_file)

    container = client.V1Container(
        name="pyssion-job-runner",
        image=image,
        command=["sh", "-c"],
        args=[cmd],
        env=env_vars,
        security_context=client.V1SecurityContext(privileged=False,capabilities=client.V1Capabilities(add=["SYS_ADMIN"])),
        volume_mounts=[client.V1VolumeMount(name=pyssion_configmap_name, mount_path="/scripts"),],
        resources=resources,
        working_dir="/app/code"
    )

    #volume build
    volume = client.V1Volume(name=pyssion_configmap_name,config_map=client.V1ConfigMapVolumeSource(name=pyssion_configmap_name))

    return container, volume

def command_builder(minio_env:dict,req_file:str=None,minio_mirror:bool=False,sync_minio:bool=False)->str:
    steps = ["echo 🚀PYSSION JOB START"]
    if minio_mirror == True:
        steps.append('cp /scripts/minio_adapter.sh /tmp/minio_adapter.sh && chmod +x /tmp/minio_adapter.sh && /tmp/minio_adapter.sh')
    
    steps.append('python3 -m venv venv')
    steps.append('venv/bin/pip install --upgrade pip minio')
    steps.append('venv/bin/python /scripts/k8s_uploader.py')
    if req_file:
        steps.append(f'venv/bin/pip install -r {req_file}')
    steps.append(f'venv/bin/python {minio_env["ENTRYPOINT_FILE"]}')
    if minio_mirror == True:
        steps.append(f"mc mirror --exclude 'venv/*' /mnt/minio myminio/{minio_env['MINIO_BUCKET']}/{minio_env['MINIO_PREFIX']}")
    steps.append("echo 🎉PYSSION JOB FINISHED")
    
    cmd = " && ".join(steps)
    return cmd

def container_env_var_builder(minio_env:dict)->list:
    return [
        client.V1EnvVar(name="PYSSION_MINIO_ENDPOINT", value=minio_env["MINIO_ENDPOINT"]),
        client.V1EnvVar(name="PYSSION_MINIO_ACCESSKEY", value=minio_env["MINIO_ACCESS"]),
        client.V1EnvVar(name="PYSSION_MINIO_SECRETKEY", value=minio_env["MINIO_SECRET"]),
        client.V1EnvVar(name="PYSSION_MINIO_BUCKET", value=minio_env["MINIO_BUCKET"]),
        client.V1EnvVar(name="PYSSION_MINIO_PREFIX", value=minio_env["MINIO_PREFIX"]),
        client.V1EnvVar(name="PYSSION_ENTRYPOINT_FILE", value=minio_env["ENTRYPOINT_FILE"]),
    ]

def container_builder(dockerfile:str,tag:str=None,docker_env:dict = None)->str:
    if docker_env == None:
        client = docker.client.from_env()
    else:
        client = docker.DockerClient(base_url=docker_env["host_url"])
    if tag == None:
        tag = generate_random_string()
    image, logs = client.images.build(path=dockerfile, tag=tag)
    try:
        for log in logs:
                if "stream" in log:
                    print(log["stream"].strip())
        print(f"✅ Successfully built image: {image.tags}")
    except BuildError as e:
        print(f"❌ Build failed: {e}")
    return image,logs,tag

#Container Time check
def timer(namespace, job_name,ignore=None):
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


#container Log View
def logviewer(namespace, job_name):
    core = client.CoreV1Api()
    pod_list = core.list_namespaced_pod(namespace, label_selector=f"job-name={job_name}")
    pod_name = pod_list.items[0].metadata.name

    logs = core.read_namespaced_pod_log(
    name=pod_name,
    namespace=namespace,
    tail_lines=None,
    limit_bytes=None
    )

    print(f"\n📦 print log (Pod: {pod_name}):\n{'-' * 30}\n{logs}\n{'-' * 30}")