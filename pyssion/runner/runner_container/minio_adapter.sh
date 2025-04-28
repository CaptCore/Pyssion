#!/bin/bash

# Only For Debian & apt repository OS
set -e

# 1. Requirement Package Install
echo "🔧 Installing dependencies..."
apt-get update && apt-get install -y \
    ca-certificates \
    wget \
    curl \
    gnupg \
    lsb-release

# 2. Download mc (MinIO Client)
echo "📥 Downloading mc (MinIO Client)..."
curl -sSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc
chmod +x /usr/local/bin/mc

# 3. MINIO ENV
RAW_ENDPOINT="${PYSSION_MINIO_ENDPOINT:-host.docker.internal:9000}"
if [[ "$RAW_ENDPOINT" =~ ^https?:// ]]; then
    ENDPOINT="$RAW_ENDPOINT"
else
    ENDPOINT="https://$RAW_ENDPOINT"
fi

ACCESS_KEY=${PYSSION_MINIO_ACCESSKEY:-minioadmin}
SECRET_KEY=${PYSSION_MINIO_SECRETKEY:-minioadmin}
BUCKET=${PYSSION_MINIO_BUCKET:-testbucket}
MOUNT_DIR=${MOUNT_DIR:-/mnt/minio}
PREFIX=${PYSSION_MINIO_PREFIX:-""}

# 4. Set Alias for MinIO
echo "🔐 Setting up mc alias..."
mc alias set myminio "$ENDPOINT" "$ACCESS_KEY" "$SECRET_KEY" --api S3v4

# 5. Prepare Mount Directory
mkdir -p "$MOUNT_DIR"
echo "📂 Make Ount Dir Successfully"

# 6. Run mc mirror (MinIO -> Local)
echo "📂 Syncing from MinIO bucket '$BUCKET/$PREFIX' to '$MOUNT_DIR'..."
mc mirror --overwrite --exclude "venv/*" "myminio/$BUCKET/$PREFIX" "$MOUNT_DIR"

# 7. Done
echo "✅ Sync completed. Contents are available at $MOUNT_DIR"
