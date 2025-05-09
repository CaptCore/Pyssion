import time
from kubernetes import client
from kubernetes.client.exceptions import ApiException


class KubernetesJobCleaner:
    def __init__(self, batch_v1_api):
        self._batch = batch_v1_api

    def delete_if_exists(
        self, namespace: str, job_name: str, wait: bool = True, timeout: int = 120
    ):
        try:
            self._batch.delete_namespaced_job(
                name=job_name,
                namespace=namespace,
                body=client.V1DeleteOptions(propagation_policy="Foreground"),
            )
            print(
                f"🗑️ Deletion requested for Job '{job_name}' in namespace '{namespace}'"
            )

            if wait:
                for i in range(timeout):
                    try:
                        self._batch.read_namespaced_job(job_name, namespace)
                        print(
                            f"⏳ Waiting for Job '{job_name}' to be deleted... ({i+1}s)"
                        )
                        time.sleep(1)
                    except ApiException as e:
                        if e.status == 404:
                            print(f"✅ Job '{job_name}' fully deleted.")
                            return True
                        else:
                            raise
                raise TimeoutError(
                    f"❌ Timed out: Job '{job_name}' was not deleted within {timeout} seconds."
                )

        except ApiException as e:
            if e.status == 404:
                print(f"ℹ️ Job '{job_name}' not found → Ready to create new.")
            else:
                raise
