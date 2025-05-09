from kubernetes import client
from kubernetes.client.exceptions import ApiException
from pathlib import Path
import math


class PVCBuilder:
    def __init__(self, pvc_name: str, storage: str = None):
        self.pvc_name = pvc_name
        self.storage = storage or "128Gi"  # default

    @staticmethod
    def calculate_size(
        project_dir: str, buffer: float = 1.2, minimum: str = "128Gi"
    ) -> str:
        project_dir = Path(project_dir)
        total_bytes = sum(
            f.stat().st_size for f in project_dir.rglob("*") if f.is_file()
        )
        total_gb = total_bytes / (1024**3) * buffer
        size_gi = max(math.ceil(total_gb * 10) / 10, 1.0)
        return f"{size_gi}Gi"

    def build(self) -> client.V1PersistentVolumeClaim:
        return client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name=self.pvc_name),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(
                    requests={"storage": self.storage}
                ),
            ),
        )


class PVCManager:
    def __init__(self, core_v1: client.CoreV1Api, namespace: str):
        self._core_v1 = core_v1
        self._namespace = namespace

    def ensure_or_resize(self, new_pvc: client.V1PersistentVolumeClaim):
        name = new_pvc.metadata.name
        try:
            existing = self._core_v1.read_namespaced_persistent_volume_claim(
                name, self._namespace
            )
            current_size = existing.spec.resources.requests["storage"]
            requested_size = new_pvc.spec.resources.requests["storage"]

            if self._compare_size(requested_size, current_size) > 0:
                print(f"📏 Resizing PVC '{name}': {current_size} → {requested_size}")
                self._core_v1.patch_namespaced_persistent_volume_claim(
                    name=name,
                    namespace=self._namespace,
                    body={
                        "spec": {"resources": {"requests": {"storage": requested_size}}}
                    },
                )
            else:
                print(f"ℹ️ PVC '{name}' already exists with size {current_size}.")
        except ApiException as e:
            if e.status == 404:
                print(f"📦 Creating PVC '{name}'")
                self._core_v1.create_namespaced_persistent_volume_claim(
                    self._namespace, new_pvc
                )
            else:
                raise

    def _compare_size(self, size1: str, size2: str) -> int:
        def to_gib(s):
            s = s.lower()
            if s.endswith("gi"):
                return float(s.replace("gi", ""))
            elif s.endswith("mi"):
                return float(s.replace("mi", "")) / 1024
            return float(s)

        return to_gib(size1) - to_gib(size2)


# Init Container
def init_container_build(minio_env: dict, volume_name: str, pvc_name: str):
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

    init_container = client.V1Container(
        name="init-data",
        image="minio/mc:latest",
        command=[
            "sh",
            "-c",
            "mc alias set S3 https://${MINIO_ENDPOINT} ${MINIO_ACCESS} ${MINIO_SECRET} && "
            "mc mirror --overwrite S3/${MINIO_BUCKET}/${MINIO_PREFIX} /data",
        ],
        env=dict_to_envvars(minio_env),
        volume_mounts=[client.V1VolumeMount(mount_path="/data", name=volume_name)],
    )
    data_volume = client.V1Volume(
        name=volume_name,
        persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
            claim_name=pvc_name
        ),
    )

    return init_container, data_volume


# Container Runner
def main_container_build(
    volume_name: str = None,
    image: str = "python",
    req_file: str = None,
    resources: client.V1ResourceRequirements = None,
    entrypoint_file: str = None,
    venv_cache: bool = False,
):
    if volume_name == None:
        raise

    # env vars build : TODO LIST (USER CUSTOM docker)
    env_vars = []

    cmd = command_build(
        req_file=req_file, entrypoint_file=entrypoint_file, venv_cache=venv_cache
    )

    container = client.V1Container(
        name="pyssion-job-runner",
        image=image,
        command=["sh", "-c"],
        args=[cmd],
        security_context=client.V1SecurityContext(
            privileged=False, capabilities=client.V1Capabilities(add=["SYS_ADMIN"])
        ),
        resources=resources,
        working_dir="/app/code",
        volume_mounts=[client.V1VolumeMount(mount_path="/app/code", name=volume_name)],
    )

    return container


def command_build(
    req_file: str = None, entrypoint_file: str = "main.py", venv_cache: bool = False
) -> str:
    steps = ["echo 🚀PYSSION JOB START"]
    steps.append("echo WORK DIR : $PWD")
    steps.append("echo ❗COPY scripts code")
    # 2. venv create
    if venv_cache == True:
        steps.append("echo 🚀 Create Python VENV")
        steps.append("python3 -m venv venv")
        steps.append("venv/bin/pip install --upgrade pip")
        # 3. install requirements
        if req_file != None:
            steps.append("echo 🚀 PYTHON env build")
            steps.append(f"venv/bin/pip install -r {req_file}")
        else:
            steps.append("echo ❗SKIPPED python env build")
    else:
        steps.append("echo 🚀 SKIP venv setup. just install pip")
        if req_file != None:
            steps.append(f"pip install -r {req_file}")

    # 4. launch entrypoint file
    steps.append("echo List of /app/code files")
    steps.append("ls")
    if venv_cache == True:
        steps.append(f"venv/bin/python {entrypoint_file}")
    else:
        steps.append(f"python3 {entrypoint_file}")

    # 6. End log
    steps.append("echo 🎉PYSSION JOB FINISHED")

    # return command
    return " && ".join(steps)


def dict_to_envvars(env_dict: dict) -> list:
    return [client.V1EnvVar(name=k, value=v) for k, v in env_dict.items()]


def container_env_var_builder(minio_env: dict) -> list:
    return [
        client.V1EnvVar(
            name="PYSSION_MINIO_ENDPOINT", value=minio_env["MINIO_ENDPOINT"]
        ),
        client.V1EnvVar(
            name="PYSSION_MINIO_ACCESSKEY", value=minio_env["MINIO_ACCESS"]
        ),
        client.V1EnvVar(
            name="PYSSION_MINIO_SECRETKEY", value=minio_env["MINIO_SECRET"]
        ),
        client.V1EnvVar(name="PYSSION_MINIO_BUCKET", value=minio_env["MINIO_BUCKET"]),
        client.V1EnvVar(name="PYSSION_MINIO_PREFIX", value=minio_env["MINIO_PREFIX"]),
    ]
