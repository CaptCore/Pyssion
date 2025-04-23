import time
import os
from kubernetes import client, config
from pathlib import Path
from kubernetes.client.rest import ApiException
        
#Container Runner
def pyssion_job_container(minio_env: dict, pyssion_configmap_name:str = None, image="python:3.11-slim", req_file: str = None):
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
    if pyssion_configmap_name == None:
        pyssion_configmap_name = "pyssion-cache-script"

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
    steps.append(f"python3 {minio_env['ENTRYPOINT_FILE']}")

    cmd = " && ".join(steps)

    container = client.V1Container(
        name="pyssion-job-runner",
        image=image,
        command=["sh", "-c"],
        args=[cmd],
        env=env_vars,
        volume_mounts=[
            client.V1VolumeMount(name=pyssion_configmap_name, mount_path="/scripts")
        ]
    )
    container.working_dir = "/app/code"
    volume = client.V1Volume(
        name=pyssion_configmap_name,
        config_map=client.V1ConfigMapVolumeSource(name=pyssion_configmap_name)
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
    namespace: str,
    name: str = None,
    file_path: str = None,
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
    if file_path == None:
        pkg_dir = Path(__file__).parent
        script_path = Path(os.path.join(pkg_dir,"runner_container/k8s_uploader.py"))
    else:
        script_path = Path(file_path)
    script_content = script_path.read_text(encoding="utf-8")
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
    except ApiException as e:
        if e.status == 409:
            # Already Exist, than process patch
            v1.patch_namespaced_config_map(name=name, namespace=namespace, body=cm)
            print(f"ConfigMap '{name}' patched (already existed).")
        else:
            raise

def ensure_pvc(core:client.CoreV1Api ,pvc_name: str, namespace: str, size: str = "1Gi", storage_class: str = None):
    """
    Create PVC
    If PVC already Exist, than Pass
    - pvc_name: str -> PVC's name
    - namespace: str -> kubernetes node namespace
    - size: Request Storage Size (example: "5Gi")
    - storage_class: StorageClass Name (None = Default)
    """
    pvc_body = client.V1PersistentVolumeClaim(
        metadata=client.V1ObjectMeta(name=pvc_name),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=client.V1ResourceRequirements(
                requests={"storage": size}
            ),
            storage_class_name=storage_class
        )
    )
    try:
        core.create_namespaced_persistent_volume_claim(
            namespace=namespace,
            body=pvc_body
        )
        print(f"✅ Create PVC '{pvc_name}'")
        return core
    except ApiException as e:
        if e.status == 409:
            print(f"ℹ️ PVC '{pvc_name}' already Created")
            return None
        else:
            raise
