from kubernetes import client
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


wk_py_code = r"""
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
import os
import requests, numpy as np, io

# PSClient 클래스 정의
class PSClient:
    def __init__(self, server_url):
        self.url = server_url.rstrip('/')
    def get_params(self):
        r = requests.get(f"{self.url}/get_params")
        r.raise_for_status()
        return np.load(io.BytesIO(r.content))
    def update_params(self, deltas):
        buf = io.BytesIO()
        np.savez(buf, **deltas)
        buf.seek(0)
        files = {'data': ('deltas.npz', buf, 'application/octet-stream')}
        r = requests.post(f"{self.url}/update_params", files=files)
        r.raise_for_status()

ps = PSClient(os.environ['PS_ENDPOINT'])

model = nn.Sequential(
    nn.Linear(28*28, 128),
    nn.ReLU(),
    nn.Linear(128, 10)
)
optimizer = optim.SGD(model.parameters(), lr=0.01)
transform = transforms.Compose([transforms.ToTensor(), transforms.Lambda(lambda t: t.view(-1,28*28))])
dataset = torchvision.datasets.MNIST('.', train=True, download=True, transform=transform)
loader  = torch.utils.data.DataLoader(dataset, batch_size=64, shuffle=True)

name_to_key = {
    '0.weight': 'w1',
    '0.bias':   'b1',
    '2.weight': 'w2',
    '2.bias':   'b2',
}

for epoch in range(3):
    for xb, yb in loader:
        optimizer.zero_grad()
        out = model(xb)
        loss = nn.CrossEntropyLoss()(out, yb)
        loss.backward()
        deltas = {}
        for name, param in model.named_parameters():
            grad = param.grad
            if grad is None:
                continue
            deltas[name_to_key[name]] = grad.detach().cpu().numpy()
        ps.update_params(deltas)
        arr = ps.get_params()
        new_state = {
            '0.weight': torch.from_numpy(arr['w1']),
            '0.bias':   torch.from_numpy(arr['b1']),
            '2.weight': torch.from_numpy(arr['w2']),
            '2.bias':   torch.from_numpy(arr['b2']),
        }
        model.load_state_dict(new_state)
    print(f"Epoch {epoch+1} complete")
"""

# 파이썬 코드를 echo로 저장 → pip 설치 → 실행 (line break 주의)
wk_cmd = (
    f"echo '{wk_py_code.replace(chr(10), r'\\n').replace('\'', '\\\'')}' > /app/train_pt.py && "
    "pip install --no-cache-dir torch torchvision requests numpy && "
    "python /app/train_pt.py"
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


def deploy_workers(apps_api, namespace, port, replica, container_image):
    # Worker 역시 동일하게 pip install + run
    wk_container = V1Container(
        name="worker",
        image=container_image,
        command=["/bin/sh", "-c", wk_cmd],
        env=[
            V1EnvVar(name="PS_ENDPOINT", value=f"http://ps-svc:{port}"),
            V1EnvVar(
                name="WORKER_ID",
                value_from=client.V1EnvVarSource(
                    field_ref=client.V1ObjectFieldSelector(field_path="metadata.name")
                ),
            ),
        ],
    )
    wk_dep = make_deployment("worker-deploy", {"app": "worker"}, replica, wk_container)
    apps_api.create_namespaced_deployment(namespace, wk_dep)
    print(f"✅ Deployment 'worker-deploy' ({replica} replicas) created")
