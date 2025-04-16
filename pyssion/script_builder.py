def generate_command_script(minio_env, entrypoint_file, req_file=None):
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

