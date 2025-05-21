from kubernetes.client import V1Service, V1ServiceSpec, V1ServicePort, V1ObjectMeta


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
