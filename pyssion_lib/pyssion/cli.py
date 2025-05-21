# pyssion/cli.py
import click
import os
from .core import Pyssion
from .manager.envloader import get_env


@click.group()
def main():
    """Pyssion CLI - Kubernetes base Python Launch Tool"""
    pass


@main.command()
@click.option("--env", type=click.Path(exists=True), help=".env file path")
@click.option("--entrypoint", required=True, help="Launch Python file (ex: main.py)")
@click.option(
    "--req", default=None, type=click.Path(exists=True), help="requirements.txt Path"
)
@click.option("--gpus", default=0, type=int, help="Usage GPU unit number")
def run(env, entrypoint, req, gpus):
    """Pyssion Job Run"""
    if env:
        env = get_env()

    minio_config = {
        "MINIO_ENDPOINT": os.getenv("PYSSION_MINIO_ENDPOINT"),
        "MINIO_ACCESS": os.getenv("PYSSION_MINIO_ACCESSKEY"),
        "MINIO_SECRET": os.getenv("PYSSION_MINIO_SECRETKEY"),
        "MINIO_BUCKET": os.getenv("PYSSION_MINIO_BUCKET"),
    }

    k8s_config = {"namespace": os.getenv("PYSSION_NAMESPACE", "default")}

    pyssion = Pyssion(
        minio_config=minio_config,
        k8s_config=k8s_config,
        entrypoint_file=entrypoint,
        req_file=req,
        gpus=gpus,
    )

    pyssion.run()


if __name__ == "__main__":
    main()
