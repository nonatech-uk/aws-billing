#!/bin/bash
# Build and run the aws-billing container.
#
# Prerequisites (on the NAS):
#   /zfs/Apps/AppData/aws-billing/.env             — DB DSN, Keycloak secrets, session secret
#   /zfs/Apps/AppData/aws-billing/aws-credentials  — ~/.aws/credentials with [org] + [tony] profiles
#
# Usage:
#   ./deploy/run.sh              # build + run
#   ./deploy/run.sh --build-only # just build

set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE="aws-billing:latest"
CONTAINER="aws-billing"
SECRETS_DIR="/zfs/Apps/AppData/aws-billing"

echo "Building $IMAGE..."
podman build -t "$IMAGE" -f Containerfile .

if [ "${1:-}" = "--build-only" ]; then
    echo "Build complete."
    exit 0
fi

if podman container exists "$CONTAINER" 2>/dev/null; then
    echo "Stopping existing container..."
    podman stop "$CONTAINER" || true
    podman rm "$CONTAINER" || true
fi

echo "Starting $CONTAINER..."
podman run -d \
    --name "$CONTAINER" \
    --restart unless-stopped \
    --network host \
    -v "$SECRETS_DIR/.env:/app/config/.env:ro" \
    -v "$SECRETS_DIR/aws-credentials:/root/.aws/credentials:ro" \
    "$IMAGE"

echo "Container started. UI at https://aws.mees.st/"
echo "Logs: podman logs -f $CONTAINER"
