#!/bin/bash
set -euo pipefail

# uvicorn binds to all interfaces; Traefik fronts it on the NAS.
exec uvicorn src.api.app:app --host 0.0.0.0 --port "${PORT:-8000}" \
    --proxy-headers --forwarded-allow-ips '*'
