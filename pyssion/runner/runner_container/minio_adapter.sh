#!/bin/bash

# Only For Debian & apt repository OS
set -e

# 1. Requirement Package Install
echo "🔧 Installing dependencies..."
apt-get update && apt-get install -y \
    fuse \
    s3fs \
    ca-certificates \
    wget \
    curl \
    gnupg \
    lsb-release

# 2. MINIO ENV
#checkup endpoint
RAW_ENDPOINT="${PYSSION_MINIO_ENDPOINT:-host.docker.internal:9000}"
if [[ "$RAW_ENDPOINT" =~ ^https?:// ]]; then
    ENDPOINT="$RAW_ENDPOINT"
else
    ENDPOINT="https://$RAW_ENDPOINT"
fi
#else
ACCESS_KEY=${PYSSION_MINIO_ACCESSKEY:-minioadmin}
SECRET_KEY=${PYSSION_MINIO_SECRETKEY:-minioadmin}
BUCKET=${PYSSION_MINIO_BUCKET:-testbucket}
MOUNT_DIR=${MOUNT_DIR:-/mnt/minio}
# 3. Setting Up S3/Minio
echo "🔐 Setting up s3fs credentials..."
echo "${ACCESS_KEY}:${SECRET_KEY}" > /root/.passwd-s3fs
chmod 600 /root/.passwd-s3fs

# 4. Mount Dir
mkdir -p "$MOUNT_DIR"

# 5. Run S3fs Mount
echo "📦 Mounting S3 bucket '$BUCKET' to '$MOUNT_DIR'..."
s3fs "$BUCKET" "$MOUNT_DIR" \
  -o passwd_file=/root/.passwd-s3fs \
  -o url="$ENDPOINT" \
  -o use_path_request_style \
  -o nonempty \
  -o allow_other

# 6. Check UP
if mountpoint -q "$MOUNT_DIR"; then
    echo "✅ Mounted successfully at $MOUNT_DIR"
else
    echo "❌ Mount failed"
    exit 1
fi
