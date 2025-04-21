import time
from kubernetes import client, config
from pathlib import Path


#Container Runner
def pyssion_job_container(minio_env: dict, image="python:3.11-slim", req_file: str = None):
    """
    - minio_env: {
    #     "MINIO_ENDPOINT": 'minio_env["MINIO_ENDPOINT"]',,
    #     "MINIO_ACCESS": "minio_env["MINIO_ACCESS"]",
    #     "MINIO_SECRET": "minio_env["MINIO_SECRET"]",
    #     "MINIO_BUCKET": "minio_env["MINIO_BUCKET"]",
    #     "MINIO_PREFIX": "minio_env["MINIO_PREFIX"]",
    #     "ENTRYPOINT_FILE": minio_env["ENTRYPOINT_FILE"]
    # }
    - req_file: req_file
    """

    # 1) EnvVars 설정
    env_vars = [
        client.V1EnvVar(name="PYSSION_MINIO_ENDPOINT", value=minio_env["MINIO_ENDPOINT"]),
        client.V1EnvVar(name="PYSSION_MINIO_ACCESSKEY", value=minio_env["MINIO_ACCESS"]),
        client.V1EnvVar(name="PYSSION_MINIO_SECRETKEY", value=minio_env["MINIO_SECRET"]),
        client.V1EnvVar(name="PYSSION_MINIO_BUCKET", value=minio_env["MINIO_BUCKET"]),
        client.V1EnvVar(name="PYSSION_MINIO_PREFIX", value=minio_env["MINIO_PREFIX"]),
        client.V1EnvVar(name="PYSSION_ENTRYPOINT_FILE", value=minio_env["ENTRYPOINT_FILE"]),
    ]

    steps = [
        "pip install minio",
        "python3 /scripts/pyssion_default.py"
    ]
    if req_file:
        steps.append(f"pip install -r {req_file}")
    steps.append(f"python3 /app/code/{minio_env['ENTRYPOINT_FILE']}")

    cmd = " && ".join(steps)

    container = client.V1Container(
        name="pyssion-job-runner",
        image=image,
        command=["sh", "-c"],
        args=[cmd],
        env=env_vars,
        volume_mounts=[
            client.V1VolumeMount(name="pyssion-cache-script", mount_path="/scripts")
        ]
    )

    volume = client.V1Volume(
        name="pyssion-cache-script",
        config_map=client.V1ConfigMapVolumeSource(name="pyssion-cache-script")
    )

    return container, volume



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


#for run container configmap, use this function
def create_configmap_from_file(
    name: str,
    namespace: str,
    file_path: str,
    key: str = None,
    config_file: str = None
):
    """
    Read ConfigMap file
    name: str ConfigMap '{name}',
    namespace: str ConfigMap '{namespace}',
    file_path: str ConfigMap '{file_path}',
    key: str = None ConfigMap '{key}',
    config_file: str = None ConfigMap '{config_file}'
    """

    # 1) Config File Load
    if config_file == None:
        config.load_kube_config()
    else:
        config.load_kube_config(config_file=config_file)

    # 3) Read File
    script_path = Path(file_path)
    script_content = script_path.read_text()
    data_key = key or script_path.name

    # 4) Create V1ConfigMap Object
    cm = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name=name),
        data={data_key: script_content}
    )

    # 5) Create ConfigMap by Request API
    v1 = client.CoreV1Api()
    try:
        v1.create_namespaced_config_map(namespace=namespace, body=cm)
        print(f"ConfigMap '{name}' created in namespace '{namespace}'.")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            # Already Exist, than process patch
            v1.patch_namespaced_config_map(name=name, namespace=namespace, body=cm)
            print(f"ConfigMap '{name}' patched (already existed).")
        else:
            raise