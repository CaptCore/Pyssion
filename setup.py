from setuptools import setup, find_packages

setup(
    name="pyssion",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "minio",
        "kubernetes"
    ],
)
