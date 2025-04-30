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
    # gpus not required,, and req_file too.
    # Need to upload req.txt, if you want to install python env
    # you can ignore some files to upload by using ".pyssionignore" file, which looks like ".gitignore" file.
    # You must setup entrypoint file. or, your entry point file's name must be setup main
    p = Pyssion(
        k8s_config={
            "config_file":"s2.yaml"
        },
        gpus=1,
        req_file="req.txt",
        entrypoint_file="tmp2.py"
    )
    p.run()

```

## requirement

- Python 3.11 or latest
- rancher / minio (or S3)
