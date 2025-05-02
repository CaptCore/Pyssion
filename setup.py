from setuptools import setup, find_packages

setup(
    name="pyssion",
    version="0.1",
    package_dir={"": "pyssion_lib"},
    packages=find_packages(where="pyssion_lib"),
    install_requires=[
        "minio",
        "kubernetes",
    ],
    include_package_data=True,
    zip_safe=False,
    author="CaptCore",
    description="A Kubernetes + MinIO automation tool for Python",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)