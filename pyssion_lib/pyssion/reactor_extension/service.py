from kubernetes.client import (
    V1Service,
    V1Deployment,
    V1EnvVar,
    V1LabelSelector,
    V1ServicePort,
    V1ContainerPort,
    V1ObjectMeta,
    V1PodSpec,
    V1ServiceSpec,
    V1PodTemplateSpec,
    V1DeploymentSpec,
    V1Container,
)


def make_service(name: str, selector: dict, port: int):
    """_summary_

    Args:
        name (str): service name, like "ps-svc"
        selector (dict): service selector, like {"app": "ps"}
        port (int): service port, like 80, or port env setting

    Returns:
        V1Service: can use kubernetes client
    """
    return V1Service(
        api_version="v1",
        kind="Service",
        metadata=V1ObjectMeta(name=name),
        spec=V1ServiceSpec(
            selector=selector, ports=[V1ServicePort(port=port, target_port=port)]
        ),
    )


def make_deployment(name: str, labels: dict, replicas: int, container: V1Container):
    template = V1PodTemplateSpec(
        metadata=V1ObjectMeta(labels=labels), spec=V1PodSpec(containers=[container])
    )
    spec = V1DeploymentSpec(
        replicas=replicas,
        selector=V1LabelSelector(match_labels=labels),
        template=template,
    )
    return V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=V1ObjectMeta(name=name),
        spec=spec,
    )


def deploy_parameter_server(
    core_api, apps_api, namespace, port, replica, container_image
):
    # Can Exchange this to builder.py -> init_container function?
    # 1) Service
    svc = make_service("ps-svc", {"app": "ps"}, port)
    core_api.create_namespaced_service(namespace, svc)
    print("✅ Service 'ps-svc' created")

    # 2) Container build
    # this part will create Parameter Server for Pyssion
    ps_cmd = "pip install --no-cache-dir Flask numpy && " "python /app/ps_server.py"
    ps_container = V1Container(
        name="ps",
        image=container_image,
        command=["/bin/sh", "-c", ps_cmd],
        ports=[V1ContainerPort(container_port=port)],
        env=[V1EnvVar(name="WORKER_REPLICAS", value=str(replica))],
    )
    ps_dep = make_deployment("ps-deploy", {"app": "ps"}, replica, ps_container)
    apps_api.create_namespaced_deployment(namespace, ps_dep)
    print(f"✅ Deployment 'ps-deploy' ({replica} replicas) created")
