import docker
from docker.errors import BuildError

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