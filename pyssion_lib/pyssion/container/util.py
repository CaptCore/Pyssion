from kubernetes.client.exceptions import ApiException


# just show job status
def status_print(batch, namespace, job_name):
    job = batch.read_namespaced_job_status(job_name, namespace)
    status = job.status
    if status.succeeded:
        print("✅ Job succeeded.")
        return True
    elif status.failed:
        print("❌ Job failed.")
        return False


def delete_pvc_and_pv(core_v1, namespace: str, pvc_name: str):
    try:
        # 먼저 PVC 객체 가져오기 (PV 이름 확인용)
        pvc = core_v1.read_namespaced_persistent_volume_claim(
            name=pvc_name, namespace=namespace
        )
        pv_name = pvc.spec.volume_name

        # PVC 삭제
        core_v1.delete_namespaced_persistent_volume_claim(
            name=pvc_name, namespace=namespace, body={}
        )
        print(f"🗑️ PVC '{pvc_name}' deleted.")

        # PV 삭제 시도
        if pv_name:
            try:
                core_v1.delete_persistent_volume(name=pv_name, body={})
                print(f"🗑️ PV '{pv_name}' deleted.")
            except ApiException as e:
                if e.status == 404:
                    print(f"ℹ️ PV '{pv_name}' already deleted.")
                else:
                    raise

    except ApiException as e:
        if e.status == 404:
            print(f"ℹ️ PVC '{pvc_name}' not found.")
        else:
            raise
