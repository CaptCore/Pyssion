import time
from kubernetes import client,config
from pathlib import Path

def pyssion_job_container(minio_env, req_file=None):
    # common command of setup minio
    COMMON_COMMAND = "pip install minio && \\\n"

    # common command of minio download
    COMMON_COMMAND += f'''python -c """ 
import os, subprocess
from pathlib import Path
from minio import Minio

client = Minio(
    '{minio_env["MINIO_ENDPOINT"]}',
    '{minio_env["MINIO_ACCESS"]}',
    '{minio_env["MINIO_SECRET"]}',
    secure=False
)

objs = client.list_objects(
    '{minio_env["MINIO_BUCKET"]}',
    prefix='{minio_env["MINIO_PREFIX"]}',
    recursive=True
)

Path('/app/code').mkdir(parents=True, exist_ok=True)

for obj in objs:
    rel = obj.object_name.replace('{minio_env["MINIO_PREFIX"]}/', '')
    dst = os.path.join('/app/code', rel)
    Path(os.path.dirname(dst)).mkdir(parents=True, exist_ok=True)
    client.fget_object('{minio_env["MINIO_BUCKET"]}', obj.object_name, dst)""" && \
'''

    if req_file != None:
        command_script = (
            f"{COMMON_COMMAND}"
            f"pip install -r {req_file} && "
        )
    command_script = (
        f"{command_script} \\\n"
        f"python3 /app/code/{minio_env["ENTRYPOINT_FILE"]}"
    )
    return command_script

# def pyssion_cache_container(minio_env, req_file=None):
#     # common command of setup minio
#     command_script = "pip install minio && \\\n"

#     # common command of minio download
#     command_script += f'''python -c s
# '''
#     return command_script

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

def logviewer(namespace, job_name):
    core = client.CoreV1Api()
    pod_list = core.list_namespaced_pod(namespace, label_selector=f"job-name={job_name}")
    pod_name = pod_list.items[0].metadata.name
    logs = core.read_namespaced_pod_log(pod_name, namespace)
    print(f"\n📦 print log (Pod: {pod_name}):\n{'-' * 30}\n{logs}\n{'-' * 30}")

def use_cache(job_name):
    volumes = [
    # emptyDir 볼륨 정의
    client.V1Volume(
        name=f"{job_name}-volume",
        empty_dir=client.V1EmptyDirVolumeSource()
    ),
        client.V1Volume(
            name=f"{job_name}-volume",
            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                claim_name="my-pvc"
            )
        )
    ]

    return volumes

def launch_cache(config_file, minio_env):
    config.load_kube_config(config_file=config_file)
    container = client.V1Container(
        name="cache-runner",
        image="python:3.9",
        command=["sh", "-c"],
        args=["pip install minio && python3 /scripts/tmp4.py"],
        env=[
            client.V1EnvVar(name="PYSSION_MINIO_ENDPOINT", value=minio_env[""]),
            client.V1EnvVar(name="PYSSION_MINIO_ACCESSKEY", value=minio_env[""]),
            client.V1EnvVar(name="PYSSION_MINIO_SECRETKEY", value=minio_env[""]),
            client.V1EnvVar(name="PYSSION_MINIO_BUCKET", value=minio_env[""]),
            client.V1EnvVar(name="PYSSION_MINIO_PREFIX", value=minio_env[""]),
        ],
        volume_mounts=[
            client.V1VolumeMount(
                name="cache-script", mount_path="/scripts"
            )
        ],
    )

    # 2) 볼륨 정의 (ConfigMap)
    volume = client.V1Volume(
        name="cache-script",
        config_map=client.V1ConfigMapVolumeSource(name="pyssion-cache-script")
    )

    # 3) PodTemplate & Job Spec
    template = client.V1PodTemplateSpec(
        spec=client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=[volume],
        )
    )
    job_spec = client.V1JobSpec(template=template, backoff_limit=0)
    job = client.V1Job(
        metadata=client.V1ObjectMeta(name="cache-download-job"),
        spec=job_spec
    )

    # 4) Job 생성
    batch_v1 = client.BatchV1Api()
    batch_v1.create_namespaced_job(namespace="default", body=job)
    print("Job 'cache-download-job' created.")

def configmap_load(name: str,namespace: str,file_path: str,key: str = None,config_file = None):
    config.load_kube_config(config_file=config_file)  

    # 3) 파일 읽기
    script_path = Path(file_path)
    script_content = script_path.read_text(encoding="utf-8")
    data_key = key or script_path.name

    # 4) V1ConfigMap 객체 생성
    cm = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name=name),
        data={data_key: script_content}
    )

    # 5) API 호출로 ConfigMap 생성
    v1 = client.CoreV1Api()
    try:
        v1.create_namespaced_config_map(namespace=namespace, body=cm)
        print(f"ConfigMap '{name}' created in namespace '{namespace}'.")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            # 이미 존재하면 덮어쓰기(patch) 처리
            v1.patch_namespaced_config_map(name=name, namespace=namespace, body=cm)
            print(f"ConfigMap '{name}' patched (already existed).")
        else:
            raise