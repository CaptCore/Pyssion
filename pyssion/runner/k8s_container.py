import time
from kubernetes import client

def pyssion_container(minio_env, entrypoint_file, req_file=None):
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
        f"python3 /app/code/{entrypoint_file}"
    )
    return command_script

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
    try:
        logs = core.read_namespaced_pod_log(pod_name, namespace)
        print(f"\n📦 print log (Pod: {pod_name}):\n{'-' * 30}\n{logs}\n{'-' * 30}")
        return True
    except Exception as e:
        print(f"Error getting logs for pod {pod_name}: {e}")
        return False
