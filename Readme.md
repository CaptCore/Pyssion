# Pyssion

`Pyssion.run()`

1. **Pack your code!**
2. **Shoot your code into kubernetes server & run your code! **

## main function

- **Easy Run**: only one method, `Pyssion.run()`
- **Automatic Container run**: Isolate each work
- **Run Server**: If you want to run your code, you can run Kubernetes Server or Your local! *If you want to run local, please install test_env.

## install

```bash
#git pull address
pip install -e .
```

## how to use

```python
#test_code.py
import sys
sys.dont_write_bytecode = True
from pyssion.core import Pyssion

if __name__ == "__main__":
    p = Pyssion(
        minio_config={
            "endpoint": "localhost:9000",  # MinIO or S3
            "access_key": "minioid",
            "secret_key": "minio1234",
            "bucket": "pyssion"
        },
        k8s_config={
            "config_file":"your_k8s_config.yaml"
        },
        gpus=1,
        req_file="req.txt",
        entrypoint_file="main.py"
    )
    #entrypoint_file not required, gpus, and req_file too.
    #you can ignore some files to upload by using ".pyssionignore" file, which looks like ".gitignore" file.
    p.run(warn_ignore=True,ssl_ignore=True)
    #ssl_ignore is just for test env, not for your code env.

```

## requirement

- Python 3.11 or latest
- rancher / minio (or S3)
