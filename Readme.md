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

```
.pyssionignore

pyssion/
test/
pyssion.egg-info/
.git/
.gitignore
*.md
.pyssionignore
*.yaml
setup.py
```

```
.pyssionenv
# --- MinIO setting ---
MINIO_ENDPOINT=minio address
MINIO_ACCESS=minio id
MINIO_SECRET=minio password
MINIO_BUCKET=minio bucket

# --- Kubernetes setting ---
K8S_CONFIG=local.yaml
K8S_NAMESPACE=default  # if you didn't set this, we will use default set.

# --- entrypoint setting ---
ENTRYPOINT_FILE= your_entrypoint.py
REQ_FILE=req.txt

# --- Resource setting ---
GPU=1 #we can use only NVIDIA, We will soon update. Sorry !

# --- venv setting ---
USE_VENV_CACHE=0

# --- pyssion Cache drop setting ---
DELETE_PVC_AFTER_JOB=1
```

```python
#test_code.py
import sys
sys.dont_write_bytecode = True
from pyssion.core import Pyssion

if __name__ == "__main__":
    # gpus not required,, and req_file too.
    # Need to upload req.txt, if you want to install python env
    # you can ignore some files to upload by using ".pyssionignore" file, which looks like ".gitignore" file.
    # You must setup entrypoint file. or, your entry point file's name must be setup main
    p = Pyssion()
    p.run()

```

## requirement

- Python 3.11 or latest
- rancher / minio (or S3)
