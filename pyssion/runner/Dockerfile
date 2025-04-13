FROM python:3.11-slim

RUN pip install minio

WORKDIR /app
COPY runner_entrypoint.py .

ENTRYPOINT ["python", "runner_entrypoint.py"]
