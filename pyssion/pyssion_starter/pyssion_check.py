from kubernetes import client,config
from kubernetes.client.exceptions import ApiException

def setup_kaniko_environment(config_file=None,namespace="default"):
    if config_file == None:
        config.load_kube_config()
        print("📦 Loaded kubeconfig from local file")
    else:
        config.load_kube_config(config_file=config_file)
        print("📦 Loaded kubeconfig from local file")

    core_api = client.CoreV1Api()
    rbac_api = client.RbacAuthorizationV1Api()
    sa_name = "pyssion-kaniko"
    try:
        core_api.read_namespaced_service_account(sa_name, namespace)
        print("✅ ServiceAccount already exists.")
    except ApiException as e:
        if e.status == 404:
            print("🚀 Creating ServiceAccount...")
            sa = client.V1ServiceAccount(metadata=client.V1ObjectMeta(name=sa_name))
            core_api.create_namespaced_service_account(namespace, sa)
        else:
            raise
    
    crb_name = "pyssion-kaniko-binding"
    try:
        rbac_api.read_cluster_role_binding(crb_name)
        print("✅ ClusterRoleBinding already exists.")
    except ApiException as e:
        if e.status == 404:
            print("🔧 Creating ClusterRoleBinding...")
            crb = client.V1ClusterRoleBinding(
                metadata=client.V1ObjectMeta(name=crb_name),
                subjects=[client.RbacV1Subject(
                    kind="ServiceAccount",
                    name=sa_name,
                    namespace=namespace
                )],
                role_ref=client.V1RoleRef(
                    kind="ClusterRole",
                    name="cluster-admin",  # for simplicity; can be restricted later
                    api_group="rbac.authorization.k8s.io"
                )
            )
            rbac_api.create_cluster_role_binding(crb)
        else:
            print("🚨 Error Occured")
            raise
